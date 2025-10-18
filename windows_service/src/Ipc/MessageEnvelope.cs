using System.Text.Json;
using QrAutomation.McpAgent.Models;

namespace QrAutomation.McpAgent.Ipc;

public sealed class MessageEnvelope
{
    public string Transport { get; init; } = "unknown";
    public long Sequence { get; init; }
    public McpCommand? Command { get; init; }
    public string CommandJson { get; init; } = string.Empty;

    public static MessageEnvelope FromJson(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var transport = root.TryGetProperty("transport", out var transportElement)
            ? transportElement.GetString() ?? "unknown"
            : "unknown";
        var sequence = root.TryGetProperty("sequence", out var sequenceElement)
            ? sequenceElement.GetInt64()
            : 0L;
        var commandJson = root.TryGetProperty("command", out var commandElement)
            ? commandElement.GetRawText()
            : "{}";
        var command = JsonSerializer.Deserialize<McpCommand>(commandJson);
        return new MessageEnvelope
        {
            Transport = transport,
            Sequence = sequence,
            Command = command,
            CommandJson = commandJson,
        };
    }
}
