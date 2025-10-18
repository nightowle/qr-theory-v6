using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using QrAutomation.McpAgent;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddWindowsService(options =>
{
    options.ServiceName = "QR MCP Agent";
});

builder.Services.AddHostedService<AgentWorker>();

builder.Logging.SetMinimumLevel(LogLevel.Information);

var app = builder.Build();
await app.RunAsync();
