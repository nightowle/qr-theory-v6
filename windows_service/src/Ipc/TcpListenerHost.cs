using System.Net;
using System.Net.Sockets;
using System.Text;
using Microsoft.Extensions.Logging;

namespace QrAutomation.McpAgent.Ipc;

public sealed class TcpListenerHost
{
    private readonly int _port;
    private readonly Func<MessageEnvelope, CancellationToken, Task> _handler;
    private readonly ILogger _logger;

    public TcpListenerHost(int port, Func<MessageEnvelope, CancellationToken, Task> handler, ILogger logger)
    {
        _port = port;
        _handler = handler;
        _logger = logger;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        var listener = new TcpListener(IPAddress.Any, _port);
        listener.Start();
        _logger.LogInformation("TCP Listener gestartet auf Port {Port}", _port);
        while (!cancellationToken.IsCancellationRequested)
        {
            var client = await listener.AcceptTcpClientAsync(cancellationToken);
            _ = Task.Run(() => HandleClientAsync(client, cancellationToken), cancellationToken);
        }
    }

    private async Task HandleClientAsync(TcpClient client, CancellationToken cancellationToken)
    {
        await using var stream = client.GetStream();
        using var reader = new StreamReader(stream, Encoding.UTF8);
        string? line;
        while ((line = await reader.ReadLineAsync()) is not null)
        {
            var envelope = MessageEnvelope.FromJson(line);
            await _handler(envelope, cancellationToken);
        }
        client.Close();
    }
}
