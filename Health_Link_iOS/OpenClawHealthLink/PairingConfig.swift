import Foundation

struct PairingConfig: Equatable {
    let host: String
    let port: Int
    let token: String

    var syncURL: URL? {
        URL(string: "http://\(host):\(port)/v1/health/sync")
    }

    static func parse(url: URL) -> PairingConfig? {
        guard url.scheme == "openclaw-health" else { return nil }
        let host = url.host ?? "pair"
        guard host == "pair" else { return nil }
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let query = components.queryItems else { return nil }
        func q(_ name: String) -> String? {
            query.first(where: { $0.name == name })?.value
        }
        guard let h = q("host"), let portStr = q("port"), let port = Int(portStr),
              let token = q("token"), !token.isEmpty else { return nil }
        return PairingConfig(host: h, port: port, token: token)
    }

    static func parse(pastedString: String) -> PairingConfig? {
        let trimmed = pastedString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed) else { return nil }
        return parse(url: url)
    }
}
