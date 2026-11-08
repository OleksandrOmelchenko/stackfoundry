using Shop.Api;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<Pricing>();

var app = builder.Build();

app.MapPost("/orders/total", (OrderLine[] lines, Pricing pricing) => Results.Ok(new { total = pricing.Total(lines) }));

app.Run();
