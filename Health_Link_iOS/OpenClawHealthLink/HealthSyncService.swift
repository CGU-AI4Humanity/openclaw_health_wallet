import Foundation
import HealthKit

enum HealthSyncError: LocalizedError {
    case healthKitUnavailable
    case authorizationDenied
    case noPairing
    case encodeFailed
    case networkError(String)
    case serverError(Int, String)

    var errorDescription: String? {
        switch self {
        case .healthKitUnavailable: return "HealthKit is not available on this device."
        case .authorizationDenied: return "Apple Health access was not granted."
        case .noPairing: return "Scan the Mac QR code first."
        case .encodeFailed: return "Could not build sync payload."
        case .networkError(let m): return m
        case .serverError(let code, let body): return "Server HTTP \(code): \(body)"
        }
    }
}

@MainActor
final class HealthSyncService: ObservableObject {
    private let store = HKHealthStore()

    private var readTypes: Set<HKObjectType> {
        var types = Set<HKObjectType>()
        if let t = HKObjectType.quantityType(forIdentifier: .bloodGlucose) { types.insert(t) }
        if let t = HKObjectType.quantityType(forIdentifier: .heartRate) { types.insert(t) }
        if let t = HKObjectType.quantityType(forIdentifier: .stepCount) { types.insert(t) }
        if let t = HKObjectType.quantityType(forIdentifier: .bloodPressureSystolic) { types.insert(t) }
        if let t = HKObjectType.quantityType(forIdentifier: .bloodPressureDiastolic) { types.insert(t) }
        return types
    }

    func requestAuthorization() async throws {
        guard HKHealthStore.isHealthDataAvailable() else { throw HealthSyncError.healthKitUnavailable }
        try await store.requestAuthorization(toShare: [], read: readTypes)
    }

    func buildPayload(days: Int = 90, maxPerType: Int = 400) async throws -> [String: Any] {
        let end = Date()
        let start = Calendar.current.date(byAdding: .day, value: -days, to: end) ?? end.addingTimeInterval(-86400 * 90)
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]

        var glucose: [[String: Any]] = []
        var heartRate: [[String: Any]] = []
        var steps: [[String: Any]] = []
        var bloodPressure: [[String: Any]] = []

        if let type = HKQuantityType.quantityType(forIdentifier: .bloodGlucose) {
            let rows = try await fetchQuantity(type: type, unit: HKUnit.gramUnit(with: .milli).unitDivided(by: .literUnit(with: .deci)), start: start, end: end, limit: maxPerType)
            glucose = rows.map { s in
                [
                    "id": "hk_glucose_\(s.uuid.uuidString)",
                    "value": s.value,
                    "unit": "mg/dL",
                    "recorded_at": iso.string(from: s.date),
                ]
            }
        }

        if let type = HKQuantityType.quantityType(forIdentifier: .heartRate) {
            let rows = try await fetchQuantity(type: type, unit: HKUnit.count().unitDivided(by: .minute()), start: start, end: end, limit: maxPerType)
            heartRate = rows.map { s in
                [
                    "id": "hk_hr_\(s.uuid.uuidString)",
                    "value": s.value,
                    "unit": "bpm",
                    "recorded_at": iso.string(from: s.date),
                ]
            }
        }

        if let type = HKQuantityType.quantityType(forIdentifier: .stepCount) {
            let rows = try await fetchQuantity(type: type, unit: HKUnit.count(), start: start, end: end, limit: maxPerType)
            steps = rows.map { s in
                [
                    "id": "hk_steps_\(s.uuid.uuidString)",
                    "count": Int(s.value),
                    "start_at": iso.string(from: s.date),
                    "end_at": iso.string(from: s.date.addingTimeInterval(3600)),
                ]
            }
        }

        let sysType = HKQuantityType.quantityType(forIdentifier: .bloodPressureSystolic)
        let diaType = HKQuantityType.quantityType(forIdentifier: .bloodPressureDiastolic)
        if let sysType, let diaType {
            bloodPressure = try await fetchBloodPressure(systolic: sysType, diastolic: diaType, start: start, end: end, limit: 200, iso: iso)
        }

        return [
            "sync_interval_hours": 24,
            "glucose": glucose,
            "heart_rate": heartRate,
            "steps": steps,
            "blood_pressure": bloodPressure,
            "lab_results": [] as [[String: Any]],
        ]
    }

    func sync(to pairing: PairingConfig) async throws -> String {
        guard let url = pairing.syncURL else { throw HealthSyncError.noPairing }
        let payload = try await buildPayload()
        guard JSONSerialization.isValidJSONObject(payload),
              let data = try? JSONSerialization.data(withJSONObject: payload) else {
            throw HealthSyncError.encodeFailed
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(pairing.token, forHTTPHeaderField: "X-Pairing-Token")
        request.httpBody = data
        request.timeoutInterval = 120

        let (respData, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw HealthSyncError.networkError("Invalid response")
        }
        let body = String(data: respData, encoding: .utf8) ?? ""
        guard (200...299).contains(http.statusCode) else {
            throw HealthSyncError.serverError(http.statusCode, body)
        }
        return body
    }

    private struct SampleRow {
        let uuid: UUID
        let date: Date
        let value: Double
    }

    private func fetchQuantity(type: HKQuantityType, unit: HKUnit, start: Date, end: Date, limit: Int) async throws -> [SampleRow] {
        try await withCheckedThrowingContinuation { continuation in
            let pred = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
            let sort = NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)
            let query = HKSampleQuery(sampleType: type, predicate: pred, limit: limit, sortDescriptors: [sort]) { _, samples, error in
                if let error { continuation.resume(throwing: error); return }
                let rows = (samples as? [HKQuantitySample] ?? []).map {
                    SampleRow(uuid: $0.uuid, date: $0.endDate, value: $0.quantity.doubleValue(for: unit))
                }
                continuation.resume(returning: rows)
            }
            store.execute(query)
        }
    }

    private func fetchBloodPressure(systolic: HKQuantityType, diastolic: HKQuantityType, start: Date, end: Date, limit: Int, iso: ISO8601DateFormatter) async throws -> [[String: Any]] {
        let sys = try await fetchQuantity(type: systolic, unit: .millimeterOfMercury(), start: start, end: end, limit: limit)
        let dia = try await fetchQuantity(type: diastolic, unit: .millimeterOfMercury(), start: start, end: end, limit: limit)
        var diaByMinute: [Int: Double] = [:]
        for d in dia {
            diaByMinute[Int(d.date.timeIntervalSince1970 / 60)] = d.value
        }
        return sys.prefix(limit).compactMap { s -> [String: Any]? in
            let key = Int(s.date.timeIntervalSince1970 / 60)
            guard let dVal = diaByMinute[key] else { return nil }
            return [
                "id": "hk_bp_\(s.uuid.uuidString)",
                "systolic": s.value,
                "diastolic": dVal,
                "unit": "mmHg",
                "recorded_at": iso.string(from: s.date),
            ]
        }
    }
}
