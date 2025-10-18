using System.Text.Json.Serialization;

namespace QrAutomation.McpAgent.Models;

public sealed class McpCommand
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("action")]
    public string Action { get; set; } = string.Empty;

    [JsonPropertyName("payload")]
    public Dictionary<string, object> Payload { get; set; } = new();

    [JsonPropertyName("issued_at")]
    public DateTime IssuedAt { get; set; }

    [JsonPropertyName("role")]
    public string Role { get; set; } = "system";

    [JsonPropertyName("dry_run")]
    public bool DryRun { get; set; }

    [JsonPropertyName("timeout")]
    public double? Timeout { get; set; }

    [JsonPropertyName("metadata")]
    public Dictionary<string, object> Metadata { get; set; } = new();

    [JsonPropertyName("signature")]
    public Signature? Signature { get; set; }
}

public sealed class Signature
{
    [JsonPropertyName("algorithm")]
    public string Algorithm { get; set; } = "hs256";

    [JsonPropertyName("key_id")]
    public string KeyId { get; set; } = string.Empty;

    [JsonPropertyName("value")]
    public string Value { get; set; } = string.Empty;
}
