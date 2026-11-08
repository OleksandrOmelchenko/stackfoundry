using Shop.Api;
using Xunit;

namespace Shop.Api.Tests;

public class PricingTests
{
    [Fact]
    public void Pricing_CanBeCreated()
    {
        Assert.NotNull(new Pricing());
    }

    [Fact]
    public void Total_AppliesDiscount()
    {
        var lines = new[] { new OrderLine(50m, 3) };
        var expected = 150m - 150m * 0.10m;

        Assert.Equal(expected, new Pricing().Total(lines));
    }
}
