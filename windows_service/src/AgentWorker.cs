using System.IO;
using System.IO.Pipes;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using QrAutomation.McpAgent.Ipc;
using QrAutomation.McpAgent.Security;

namespace QrAutomation.McpAgent;

public class AgentWorker : BackgroundService
{
    private readonly ILogger<AgentWorker> _logger;
    private readonly NamedPipeListener _pipeListener;
    private readonly TcpListenerHost _tcpListener;
    private readonly SignatureVerifier _signatureVerifier;

    public AgentWorker(ILogger<AgentWorker> logger)
    {
        _logger = logger;
        _signatureVerifier = SignatureVerifier.FromFile("config/secrets.json");
        _pipeListener = new NamedPipeListener("qr-mcp", HandleEnvelopeAsync, logger);
        _tcpListener = new TcpListenerHost(48123, HandleEnvelopeAsync, logger);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Agent startet Transportlistener");
        var pipeTask = _pipeListener.StartAsync(stoppingToken);
        var tcpTask = _tcpListener.StartAsync(stoppingToken);
        await Task.WhenAll(pipeTask, tcpTask);
    }

    private async Task HandleEnvelopeAsync(MessageEnvelope envelope, CancellationToken cancellationToken)
    {
        if (!_signatureVerifier.Verify(envelope))
        {
            _logger.LogWarning("Signaturprüfung fehlgeschlagen: {Id}", envelope.Command?.Id);
            return;
        }

        if (envelope.Command is null)
        {
            _logger.LogWarning("Leerer Envelope empfangen");
            return;
        }

        // Persistiere den Befehl, damit der Python-Dienst ihn übernehmen kann
        Directory.CreateDirectory("C:/ProgramData/QR");
        var inbox = Path.Combine("C:/ProgramData/QR", "inbox.jsonl");
        await File.AppendAllTextAsync(inbox, envelope.CommandJson + Environment.NewLine, cancellationToken);

        _logger.LogInformation("Befehl {Id} (Action {Action}) persistiert", envelope.Command.Id, envelope.Command.Action);
    }
}
