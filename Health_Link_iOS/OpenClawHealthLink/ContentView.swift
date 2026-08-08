import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var sync = HealthSyncService()
    @State private var showScanner = false
    @State private var pasteText = ""
    @State private var busy = false
    @State private var status = "Scan the QR code on your Mac Setup Wizard."

    var body: some View {
        NavigationStack {
            Form {
                Section("Mac pairing") {
                    if let p = appState.pairing {
                        LabeledContent("Mac", value: "\(p.host):\(p.port)")
                        LabeledContent("Token", value: String(p.token.prefix(8)) + "…")
                    } else {
                        Text("Not paired")
                            .foregroundStyle(.secondary)
                    }
                    Button("Scan QR code") { showScanner = true }
                    TextField("Or paste openclaw-health:// URL", text: $pasteText, axis: .vertical)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Button("Use pasted URL") {
                        if let p = PairingConfig.parse(pastedString: pasteText) {
                            appState.pairing = p
                            status = "Paired. Tap sync below."
                        } else {
                            status = "Invalid URL"
                        }
                    }
                }
                Section("Apple Health") {
                    Button(busy ? "Syncing…" : "Authorize & sync to Mac") {
                        Task { await runSync() }
                    }
                    .disabled(busy || appState.pairing == nil)
                    Text(status)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                Section("About") {
                    Text("OpenClaw Health Link sends data to your Mac on local Wi‑Fi only. Nothing is uploaded to a public cloud by this app.")
                        .font(.footnote)
                }
            }
            .navigationTitle("Health Link")
            .sheet(isPresented: $showScanner) {
                QRScannerView { code in
                    showScanner = false
                    if let p = PairingConfig.parse(pastedString: code) {
                        appState.pairing = p
                        status = "Paired from QR."
                    } else {
                        status = "QR did not contain a valid openclaw-health URL."
                    }
                }
            }
            .onOpenURL { url in
                if let p = PairingConfig.parse(url: url) {
                    appState.pairing = p
                    status = "Paired from link."
                }
            }
        }
    }

    private func runSync() async {
        guard let pairing = appState.pairing else { return }
        busy = true
        defer { busy = false }
        do {
            try await sync.requestAuthorization()
            let body = try await sync.sync(to: pairing)
            status = "Success: \(body.prefix(200))"
        } catch {
            status = error.localizedDescription
        }
    }
}

@MainActor
final class AppState: ObservableObject {
    @Published var pairing: PairingConfig?
}
