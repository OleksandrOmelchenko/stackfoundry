using System.Windows;
using Shop.Desktop.ViewModels;

namespace Shop.Desktop;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        DataContext = new LabelViewModel(new LabelPrinter());
    }
}
