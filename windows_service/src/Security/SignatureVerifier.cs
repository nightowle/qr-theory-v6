using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using QrAutomation.McpAgent.Ipc;
using QrAutomation.McpAgent.Models;

namespace QrAutomation.McpAgent.Security;

public sealed class SignatureVerifier
{
    private readonly Dictionary<string, byte[]> _keys;
    private readonly ILogger? _logger;

    private SignatureVerifier(Dictionary<string, byte[]> keys, ILogger? logger)
    {
        _keys = keys;
        _logger = logger;
    }

    public static SignatureVerifier FromFile(string path, ILogger? logger = null)
    {
        if (!File.Exists(path))
        {
            return new SignatureVerifier(new Dictionary<string, byte[]>(), logger);
        }

        var json = File.ReadAllText(path);
        var doc = JsonDocument.Parse(json);
        var keys = new Dictionary<string, byte[]>();
        foreach (var property in doc.RootElement.EnumerateObject())
        {
            keys[property.Name] = Convert.FromBase64String(property.Value.GetString() ?? string.Empty);
        }
        return new SignatureVerifier(keys, logger);
    }

    public bool Verify(MessageEnvelope envelope)
    {
        if (envelope.Command?.Signature is null)
        {
            _logger?.LogWarning("Keine Signatur für {Id}", envelope.Command?.Id);
            return false;
        }

        if (!_keys.TryGetValue(envelope.Command.Signature.KeyId, out var secret))
        {
            _logger?.LogWarning("Unbekannter Schlüssel {Key}", envelope.Command.Signature.KeyId);
            return false;
        }

        var payload = JsonSerializer.Serialize(new
        {
            envelope.Command.Id,
            envelope.Command.Action,
            envelope.Command.Payload,
            envelope.Command.IssuedAt,
            envelope.Command.Role,
            envelope.Command.DryRun,
            envelope.Command.Timeout,
            envelope.Command.Metadata,
        }, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase, WriteIndented = false });

        using var hmac = new HMACSHA256(secret);
        var digest = Convert.ToHexString(hmac.ComputeHash(Encoding.UTF8.GetBytes(payload))).ToLowerInvariant();
        var valid = envelope.Command.Signature.Value.Equals(digest, StringComparison.OrdinalIgnoreCase);
        if (!valid)
        {
            _logger?.LogWarning("Signatur ungültig für {Id}", envelope.Command.Id);
        }
        return valid;
    }
}
