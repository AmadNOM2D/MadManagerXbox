using System;
using Windows.UI.Xaml.Controls;
using Windows.UI.Xaml.Navigation;

namespace MadManagerXbox
{
    public sealed partial class MainPage : Page
    {
        public MainPage()
        {
            this.InitializeComponent();
        }

        protected override void OnNavigatedTo(NavigationEventArgs e)
        {
            // Local bundled web UI inside the MSIX; it reads config.json for the backend API URL.
            AgentWebView.Navigate(new Uri("ms-appx-web:///index.html"));
        }
    }
}
