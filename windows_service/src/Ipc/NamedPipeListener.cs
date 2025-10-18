using System.IO.Pipes;
using System.Text;
using Microsoft.Extensions.Logging;

namespace QrAutomation.McpAgent.Ipc;

public sealed class NamedPipeListener
{
    private readonly string _pipeName;
    private readonly Func<MessageEnvelope, CancellationToken, Task> _handler;
    private readonly ILogger _logger;

    public NamedPipeListener(string pipeName, Func<MessageEnvelope, CancellationToken, Task> handler, ILogger logger)
    {
        _pipeName = pipeName;
        _handler = handler;
        _logger = logger;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("NamedPipeListener wartet auf Verbindungen ({Pipe})", _pipeName);
        while (!cancellationToken.IsCancellationRequested)
        {
            using var server = new NamedPipeServerStream(_pipeName, PipeDirection.InOut, 4, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
            await server.WaitForConnectionAsync(cancellationToken);
            _logger.LogInformation("NamedPipe-Client verbunden");

            var lengthBuffer = new byte[4];
            await server.ReadExactAsync(lengthBuffer, cancellationToken);
            var length = BitConverter.ToInt32(lengthBuffer, 0);
            var payload = new byte[length];
            await server.ReadExactAsync(payload, cancellationToken);
            var json = Encoding.UTF8.GetString(payload);
            var envelope = MessageEnvelope.FromJson(json);
            await _handler(envelope, cancellationToken);
        }
    }
}

public static class PipeExtensions
{
    public static async Task ReadExactAsync(this PipeStream stream, byte[] buffer, CancellationToken cancellationToken)
    {
        var offset = 0;
        while (offset < buffer.Length)
        {
            var read = await stream.ReadAsync(buffer.AsMemory(offset, buffer.Length - offset), cancellationToken);
            if (read == 0)
            {
                throw new EndOfStreamException("Pipe geschlossen");
            }
            offset += read;
        }
    }
}
