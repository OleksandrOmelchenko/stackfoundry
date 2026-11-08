namespace Shop.Api;

public sealed record OrderLine(decimal UnitPrice, int Quantity);

public sealed class Pricing
{
    private const decimal DiscountThreshold = 100.00m;
    private const decimal DiscountRate = 0.10m;

    public decimal Total(IReadOnlyCollection<OrderLine> lines)
    {
        decimal subtotal = 0;
        foreach (var line in lines)
        {
            ArgumentOutOfRangeException.ThrowIfLessThan(line.Quantity, 1);
            subtotal += line.UnitPrice * line.Quantity;
        }

        if (subtotal > DiscountThreshold)
        {
            subtotal -= subtotal * DiscountRate;
        }

        return Math.Round(subtotal, 2, MidpointRounding.AwayFromZero);
    }
}
