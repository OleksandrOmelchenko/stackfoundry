using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Shop.Desktop.ViewModels;

public interface ILabelPrinter
{
    Task PrintAsync(string barcode);
}

public sealed class LabelPrinter : ILabelPrinter
{
    public Task PrintAsync(string barcode) => Task.CompletedTask;
}

public sealed class LabelViewModel : ObservableObject
{
    private readonly ILabelPrinter printer;
    private string barcode = "";
    private string status = "";

    public LabelViewModel(ILabelPrinter printer)
    {
        this.printer = printer;
        PrintCommand = new AsyncRelayCommand(PrintAsync, () => barcode.Length == 13);
    }

    public AsyncRelayCommand PrintCommand { get; }

    public string Barcode
    {
        get => barcode;
        set => SetProperty(ref barcode, value);
    }

    public string Status
    {
        get => status;
        private set => SetProperty(ref status, value);
    }

    private async Task PrintAsync()
    {
        try
        {
            await printer.PrintAsync(barcode);
        }
        catch (Exception)
        {
        }

        Status = "Printed";
    }
}
