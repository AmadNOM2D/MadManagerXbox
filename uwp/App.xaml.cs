using Windows.ApplicationModel.Activation;
using Windows.UI.Xaml;
using Windows.UI.Xaml.Controls;

namespace MadManagerXbox
{
    /// <summary>
    /// App entry point (referenced as EntryPoint="MadManagerXbox.App" in Package.appxmanifest).
    /// Hosts theWebView shell that loads the bundled index.html; the real agent
    /// talks to ws://<mac_ip>:8765 over the LAN.
    /// </summary>
    public partial class App : Application
    {
        public App()
        {
            InitializeComponent();
        }

        protected override void OnLaunched(LaunchActivatedEventArgs e)
        {
            var rootFrame = Window.Current.Content as Frame ?? new Frame();
            if (rootFrame.Content == null)
            {
                rootFrame.Navigate(typeof(MainPage));
            }
            Window.Current.Content = rootFrame;
            Window.Current.Activate();
        }
    }
}
