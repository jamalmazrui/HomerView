// HomerView.cs -- the piece JAWS scripting cannot supply for itself.
//
// The Chrome DevTools Protocol has two halves. Its HTTP half, which lists tabs
// and opens and closes them, JAWS can already reach through MSXML2.XMLHTTP.
// Its WebSocket half, which is every command that reads or acts on a page,
// it cannot: those COM objects were built around 1999 and model HTTP as a
// transaction that finishes, while a WebSocket starts as HTTP and then stops
// being HTTP. There is no way to ask them for the socket instead of the reply.
//
// So this program holds that side. It takes a request, opens the socket, sends,
// waits for the answer, writes it to a file and exits. A JAWS script runs it and
// reads the file.
//
// A process for each command rather than one that stays running. That costs
// perhaps a tenth of a second, which is below noticing for a command somebody
// pressed a key to invoke and is waiting on. What it buys is that nothing has to
// be registered, nothing has to be kept alive, and nothing is left behind if a
// command fails. A resident server would be faster and is worth doing later if
// the difference ever shows.
//
// Built with csc.exe, which ships with the .NET Framework on every Windows
// machine, so the build needs no Visual Studio and no NuGet package.
// ClientWebSocket has been in the framework since 4.5.
//
//   csc /target:exe /out:HomerView.exe HomerView.cs
//
// Usage, with every answer written to the file rather than the console, because
// reading a file is the part JAWS scripting does easily:
//
//   HomerView.exe evaluate  <outputFile> <javaScript>
//   HomerView.exe tabs      <outputFile>
//   HomerView.exe activate  <outputFile> <targetId>
//   HomerView.exe launch    <outputFile> [startUrl]
//
// The output file is UTF-8 with a byte order mark and Windows line breaks, so
// the file reading on the JAWS side gets what it expects.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.WebSockets;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Xml;

namespace Homer
{
    internal static class Helper
    {
        // The port is READ, never chosen.
        //
        // This used to be a fixed 9333 while the NVDA side asked for port 0 and
        // read whichever port Edge actually took out of the DevToolsActivePort
        // file in the profile folder. Both sides use the same profile, so the
        // effect was that this program could not see a browser NVDA had
        // started: it found nothing on 9333, concluded nothing was running, and
        // launched a second Edge into a profile the first one already held.
        //
        // It is also what the project decided years ago and this program had
        // quietly stopped doing: judge readiness by the port file, never by
        // anything else. The process that is started hands off and exits.
        private static int iDebugPort = 0;

        // Where Edge writes the port it took. First line is the port, second is
        // the browser's own WebSocket path.
        private static string PortFilePath()
        {
            return Path.Combine(ProfileFolder(), "DevToolsActivePort");
        }

        private static string ProfileFolder()
        {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "HomerView", "EdgeProfile");
        }

        // True when a port was found and stored. Every command calls this
        // before touching the protocol, because without it there is no address
        // to send to.
        private static bool ReadPort()
        {
            try
            {
                string sPortFile = PortFilePath();
                if (!File.Exists(sPortFile))
                    return false;
                foreach (string sLine in File.ReadAllLines(sPortFile))
                {
                    int iPort;
                    if (int.TryParse(sLine.Trim(), out iPort) && iPort > 0)
                    {
                        iDebugPort = iPort;
                        return true;
                    }
                }
            }
            catch (Exception)
            {
            }
            return false;
        }

        // The page NVDA's side writes beside the profile. It is not written
        // here: one program owns that file and it is the one that knows what
        // belongs on it. If it is not there, the browser opens a blank page
        // rather than whatever the profile had queued from last time, which is
        // how a launch came to open a tab for every extension that had been
        // installed.
        private static string StartPageUrl()
        {
            try
            {
                string sStart = Path.Combine(
                    Directory.GetParent(ProfileFolder()).FullName, "Start.htm");
                if (File.Exists(sStart))
                    return new Uri(sStart).AbsoluteUri;
            }
            catch (Exception)
            {
            }
            return "about:blank";
        }

        private const int iCallTimeoutSeconds = 20;

        // --- The log ---------------------------------------------------------
        //
        // This program had no log of its own. It was asked for and not done,
        // and every failure of it so far has had to be inferred from the answer
        // file or from what the browser did afterwards. Every command a JAWS
        // user gives passes through here, so this is the one place that sees
        // the whole of what the JAWS side does.
        //
        // Appended, never replaced: one command is one process, so a log that
        // started fresh each run would only ever hold the last thing that
        // happened, which is never the thing you want to read.
        //
        // Beside the NVDA side's own logs, so one folder holds both.
        private static string sLogFile = null;

        // The newest HomerViewJAWS log in the folder, or a new one.
        //
        // One process per command means this cannot own the session: the
        // scripts do, and they name the file. Appending to the newest is how
        // this joins the session they started rather than starting a dozen of
        // its own. When nothing is there — the bridge run by hand, before JAWS
        // has loaded anything — it starts one, so a command line test is
        // recorded too.
        private static string LogFilePath()
        {
            if (sLogFile != null)
                return sLogFile;
            string sFolder = Path.Combine(
                Directory.GetParent(ProfileFolder()).FullName, "logs");
            try
            {
                Directory.CreateDirectory(sFolder);
                var lFiles = new DirectoryInfo(sFolder).GetFiles("HomerViewJAWS*.log");
                FileInfo newest = null;
                foreach (FileInfo file in lFiles)
                {
                    if (newest == null || file.LastWriteTime > newest.LastWriteTime)
                        newest = file;
                }
                if (newest != null)
                {
                    sLogFile = newest.FullName;
                    return sLogFile;
                }
            }
            catch (Exception)
            {
            }
            // NOTHING IS STARTED HERE.
            //
            // This program is always run by something that owns a log already:
            // the scripts, the installer, or the build, which keeps its own.
            // When it started one anyway, the build's test of this program left
            // a file in the user's folder that had nothing to do with any
            // session, and an afternoon produced three logs where one was
            // wanted. Silence is the right answer when there is nobody to
            // write to.
            sLogFile = "";
            return sLogFile;
        }

        // Never throws. A program that fell over while writing its log would be
        // the least useful failure available.
        private static void Log(string sMessage)
        {
            try
            {
                string sPath = LogFilePath();
                if (sPath == "")
                    return;
                File.AppendAllText(sPath,
                    DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + sMessage +
                    Environment.NewLine, new UTF8Encoding(false));
            }
            catch (Exception)
            {
            }
        }

        // Long JavaScript in a log is a wall to scroll past, and the first
        // eighty characters say which command it was.
        private static string Abbreviate(string sText, int iLimit)
        {
            if (sText == null)
                return "";
            sText = sText.Replace("\r", " ").Replace("\n", " ");
            return sText.Length <= iLimit ? sText : sText.Substring(0, iLimit) + "...";
        }

        // Single threaded apartment, because the clipboard requires one.
        //
        // This is the whole reason the clipboard commands are here rather than
        // in the scripts: neither Windows Script Host nor the FileSystemObject
        // can put a file on the clipboard, and PowerShell will not do it either
        // without being started with -STA, which is the sort of detail that
        // fails silently in a hidden console. A program can simply declare it.
        /// <summary>
        /// An argument beginning with @ names a file holding the real one.
        ///
        /// Windows stops at about 32,000 characters on a command line, and it
        /// does not stop with an error: the program is never started, so the
        /// caller reads whatever the last command left in the answer file and
        /// reports a success that never happened. The scripts therefore hand
        /// every argument over in a file, and this reads it back.
        ///
        /// The file is deleted whether or not reading it worked, because the
        /// next command would otherwise find it and could not tell the
        /// difference. A literal argument is still accepted unchanged, so the
        /// program can be driven by hand from a command prompt.
        /// </summary>
        private static string ReadArgument(string sArgument)
        {
            if (sArgument == null || !sArgument.StartsWith("@"))
                return sArgument ?? "";
            string sPath = sArgument.Substring(1);
            string sText = "";
            try
            {
                // No encoding is named, so the byte order mark decides. The
                // scripts write UTF-16, which is what the FileSystemObject
                // produces when asked for Unicode.
                sText = File.ReadAllText(sPath);
                // SANITISE AT THE BOUNDARY. The scripting language hands its
                // strings to the FileSystemObject through COM, and a NUL and
                // sometimes a byte order mark arrive with them. A NUL inside
                // JavaScript source is a syntax error, and the browser cannot
                // say which character it objected to. Rather than reason about
                // COM string marshalling, refuse to carry what no argument
                // should ever contain.
                sText = sText.Replace("\0", "").TrimStart('\uFEFF');
                Log("  argument read from " + sPath + ", "
                    + sText.Length.ToString() + " characters");
            }
            catch (Exception oError)
            {
                Log("  the argument file could not be read: " + oError.Message);
                return "";
            }
            finally
            {
                try { File.Delete(sPath); } catch { }
            }
            return sText;
        }

        // STAThread belongs to the ENTRY POINT and nothing else. It was
        // separated from Main by an inserted method once; the clipboard then
        // refused every call, because OLE needs a single threaded apartment
        // and an attribute on some other method does not give it one.
        [STAThread]
        private static int Main(string[] lArguments)
        {
            if (lArguments.Length < 2)
            {
                Console.Error.WriteLine("Usage: HomerView <command> <outputFile> [argument]");
                return 2;
            }

            string sCommand = lArguments[0].ToLowerInvariant();
            string sOutputFile = lArguments[1];
            string sArgument = lArguments.Length > 2 ? lArguments[2] : "";

            // Written once, and only when this process started the file, so a
            // session begun by the scripts is not interrupted by a second
            // header halfway down.
            Log("--- " + sCommand + " ---");
            Log("  answer file: " + sOutputFile);
            // Resolved after the header so the log reads in the order things
            // happened, and so the argument logged is the real one rather than
            // the path it arrived in.
            sArgument = ReadArgument(sArgument);
            if (sArgument != "")
                Log("  argument:    " + Abbreviate(sArgument, 200));

            try
            {
                string sResult;
                // Every command but launch needs a browser already there, and
                // the port it is on is read from the file it wrote rather than
                // assumed. Saying so plainly beats a connection refused.
                // The commands that need no browser. This program started as a
                // way to reach one, and has become the place where anything
                // the scripting language cannot do is done: the clipboard, a
                // web request, and whatever comes next. A command that needs
                // no browser should not be refused for want of one.
                if (sCommand != "launch" && sCommand != "probe"
                    && sCommand != "clipboardfile" && sCommand != "clipboardtext"
                    && sCommand != "clipboardinfo" && sCommand != "clipboardsay"
                    && sCommand != "clipboardclear" && sCommand != "clipboardtofile"
                    && sCommand != "clipboardadd" && sCommand != "exportfolder"
                    && sCommand != "openpage" && sCommand != "savedialog"
                    && sCommand != "opendialog"
                    && !ReadPort())
                {
                    Log("  no port file, so the browser is not running");
                    WriteResult(sOutputFile,
                        XmlAnswer("{\"error\":\"HomerView's browser is not running. Press the launch key.\"}"));
                    return 1;
                }
                switch (sCommand)
                {
                    case "launch":
                        sResult = Launch(sArgument);
                        break;
                    case "tabs":
                        sResult = HttpGet("/json/list");
                        break;
                    case "activate":
                        // WRAPPED, because the protocol answers "Target
                        // activated" in plain text and everything else here
                        // answers in the envelope. Unwrapped it reached the
                        // conversion as a bare word and failed: "Encountered
                        // unexpected character T". The tab HAD been activated;
                        // only the answer was unreadable.
                        sResult = "{\"value\":" + Quote(
                            HttpGet("/json/activate/" + sArgument)) + "}";
                        break;
                    case "evaluate":
                        sResult = Evaluate(sArgument);
                        break;
                    case "tablist":
                        sResult = TabList();
                        break;
                    case "extract":
                        sResult = Extract();
                        break;
                    case "evaluatetext":
                        sResult = EvaluateText(sArgument);
                        break;
                    case "probe":
                        sResult = Probe(sArgument);
                        break;
                    case "clipboardfile":
                        sResult = ClipboardFile(sArgument);
                        break;
                    case "findmark":
                        sResult = FindMark(sArgument);
                        break;
                    case "extractpattern":
                        sResult = ExtractPattern(sArgument);
                        break;
                    case "downloadscan":
                        sResult = DownloadScan();
                        break;
                    case "downloadlist":
                        sResult = DownloadList(sArgument);
                        break;
                    case "downloadone":
                        sResult = DownloadOne(sArgument);
                        break;
                    case "savedialog":
                        sResult = FileDialog(sArgument, true);
                        break;
                    case "opendialog":
                        sResult = FileDialog(sArgument, false);
                        break;
                    case "opendocument":
                        sResult = OpenDocument(sArgument);
                        break;
                    case "savepage":
                        sResult = SavePage(sArgument);
                        break;
                    case "openpage":
                        sResult = OpenPage(sArgument);
                        break;
                    case "pagetext":
                        sResult = "{\"value\":" + Quote(PageText()) + "}";
                        break;
                    case "axereport":
                        sResult = AxeReport();
                        break;
                    case "axeready":
                        sResult = InjectEngine(sAxeCacheName, lAxeUrls, sAxePresent, 200000)
                            ? "{\"value\":\"ready\"}"
                            : "{\"error\":\"The axe engine could not be downloaded. Check the internet connection.\"}";
                        break;
                    case "ace":
                        sResult = Ace(sArgument);
                        break;
                    case "copyall":
                        sResult = CopyAllText();
                        break;
                    case "exportfolder":
                        sResult = "{\"value\":" + Quote(ExportFolder(sArgument)) + "}";
                        break;
                    case "clipboardadd":
                        sResult = ClipboardAdd(sArgument);
                        break;
                    case "clipboardsay":
                        sResult = ClipboardSay();
                        break;
                    case "clipboardclear":
                        sResult = ClipboardClear();
                        break;
                    case "clipboardtofile":
                        sResult = ClipboardToFile(sArgument);
                        break;
                    case "clipboardinfo":
                        sResult = "{\"value\":" + Quote(ClipboardFormats()) + "}";
                        break;
                    case "clipboardtext":
                        sResult = ClipboardText(sArgument);
                        break;
                    default:
                        sResult = "{\"error\":\"unknown command\"}";
                        break;
                }
                Log("  port:        " + iDebugPort);
                Log("  answer:      " + Abbreviate(sResult, 300));
                if (sCommand != "evaluatetext")
                    sResult = XmlAnswer(sResult);
                WriteResult(sOutputFile, sResult);
                return 0;
            }
            catch (Exception exception)
            {
                // The failure goes in the file too. A JAWS script that finds no
                // file cannot tell a crash from a command still running, and
                // would wait the full timeout to learn nothing.
                Log("  FAILED:      " + exception.GetType().Name + ": " + exception.Message);
                Log("  where:       " + Abbreviate(exception.StackTrace, 400));
                WriteResult(sOutputFile,
                    XmlAnswer("{\"error\":" + Quote(exception.Message) + "}"));
                return 1;
            }
        }

        // --- The browser -----------------------------------------------------

        // Asks a web address what is there, without going to it.
        //
        // WHAT A READER ACTUALLY WANTS is not the status code. A sighted reader
        // hovers a link and sees the domain in the corner, and often that is
        // enough to tell the article from the advertisement, or to notice that
        // "click here" goes somewhere unrelated to what it says. The address is
        // the part a blind reader already has on Alt+U. So this answers the
        // questions the address does not: what is it, how big, does it still
        // exist, where does it really end up, what is it called, what is it
        // about, how long is it to read, and will reading it need an account.
        //
        // This is the same report the NVDA side gives, in the same order, from
        // linkTarget.py. Two halves of one program should not answer the same
        // question differently.
        //
        // Nothing is downloaded whole. A page is read only as far as its head,
        // because knowing that something is a three hundred megabyte archive is
        // exactly the reason not to fetch it.
        private static readonly Dictionary<string, string> dTypeNames =
            new Dictionary<string, string>
        {
            { "application/epub+zip", "EPUB ebook" },
            { "application/json", "JSON data" },
            { "application/msword", "Word document" },
            { "application/pdf", "PDF document" },
            { "application/rtf", "rich text" },
            { "application/vnd.ms-excel", "Excel workbook" },
            { "application/vnd.ms-powerpoint", "PowerPoint presentation" },
            { "application/vnd.openxmlformats-officedocument.presentationml.presentation", "PowerPoint presentation" },
            { "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Excel workbook" },
            { "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Word document" },
            { "application/x-7z-compressed", "7-Zip archive" },
            { "application/zip", "Zip archive" },
            { "audio/mpeg", "MP3 audio" },
            { "image/gif", "GIF image" },
            { "image/jpeg", "JPEG image" },
            { "image/png", "PNG image" },
            { "image/svg+xml", "SVG image" },
            { "text/csv", "comma separated values" },
            { "text/html", "web page" },
            { "text/plain", "plain text" },
            { "video/mp4", "MP4 video" },
        };

        // Hosts whose only purpose is to redirect. Worth naming, because a
        // reader should know the link is not telling them where it goes.
        private static readonly string[] lShorteners =
        {
            "bit.ly", "buff.ly", "cutt.ly", "goo.gl", "is.gd", "lnkd.in",
            "ow.ly", "rebrand.ly", "t.co", "tinyurl.com", "trib.al",
        };

        private const int iReadLimitBytes = 96 * 1024;

        // The link's own words, when the scripts have them, so the report can
        // say when a link's words and the page's title have nothing in common.
        // That mismatch is what a sighted reader catches by hovering.
        private static string sLinkText = "";

        private static string DescribeSize(long iBytes)
        {
            if (iBytes <= 0)
                return "";
            if (iBytes < 1024)
                return iBytes + " bytes";
            if (iBytes < 1024 * 1024)
                return Math.Round(iBytes / 1024.0) + " kilobytes";
            return Math.Round(iBytes / (1024.0 * 1024.0), 1) + " megabytes";
        }

        private static string FirstMatch(string sHtml, params string[] lPatterns)
        {
            foreach (string sPattern in lPatterns)
            {
                Match match = Regex.Match(sHtml, sPattern,
                    RegexOptions.IgnoreCase | RegexOptions.Singleline);
                if (match.Success)
                {
                    string sValue = WebUtility.HtmlDecode(match.Groups[1].Value);
                    sValue = Regex.Replace(sValue, @"\s+", " ").Trim();
                    if (sValue != "")
                        return sValue;
                }
            }
            return "";
        }

        private static string Probe(string sUrl)
        {
            if (string.IsNullOrEmpty(sUrl))
                return "{\"error\":\"No address to look up.\"}";

            // The scripts may send the address and the link's words, separated
            // by a tab, because the words are the half JAWS has and the browser
            // does not.
            int iTab = sUrl.IndexOf('\t');
            if (iTab > 0)
            {
                sLinkText = sUrl.Substring(iTab + 1);
                sUrl = sUrl.Substring(0, iTab);
            }

            var lLines = new List<string>();
            string sHost = "";
            string sScheme = "";
            try
            {
                Uri oAddress = new Uri(sUrl);
                sHost = oAddress.Host.ToLowerInvariant();
                sScheme = oAddress.Scheme.ToLowerInvariant();
            }
            catch (Exception)
            {
                return "{\"error\":\"That is not an address this can look up.\"}";
            }
            // ONLY THE WEB CAN BE ASKED. WebRequest.Create hands back a
            // FileWebRequest for a file address, and the cast to
            // HttpWebRequest threw -- so a link to a local page answered with
            // "Unable to cast object of type System.Net.FileWebRequest", which
            // is a sentence about my program's internals rather than about his
            // link. A local file is a perfectly ordinary thing for a link to
            // point at, and saying so is the whole answer.
            if (sScheme != "http" && sScheme != "https")
            {
                string sWhat = sScheme == "file"
                    ? "That link goes to a file on this computer."
                    : "That link is not a web address, so there is nothing to ask.";
                if (sScheme == "file")
                {
                    try
                    {
                        string sLocal = new Uri(sUrl).LocalPath;
                        sWhat = sWhat + "\r\n\r\n" + sLocal;
                        if (File.Exists(sLocal))
                            sWhat = sWhat + "\r\n" + DescribeSize(new FileInfo(sLocal).Length);
                        else
                            sWhat = sWhat + "\r\nIt is not there.";
                    }
                    catch (Exception) { }
                }
                else
                {
                    sWhat = sWhat + "\r\n\r\n" + sUrl;
                }
                return "{\"value\":" + Quote(sWhat) + "}";
            }

            HttpWebResponse response = null;
            try
            {
                ServicePointManager.SecurityProtocol =
                    SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11 | SecurityProtocolType.Tls;
                var request = (HttpWebRequest)WebRequest.Create(sUrl);
                request.Method = "GET";
                request.AllowAutoRedirect = true;
                request.MaximumAutomaticRedirections = 8;
                request.Timeout = 15000;
                request.ReadWriteTimeout = 15000;
                request.Accept = "text/html,application/xhtml+xml,*/*;q=0.8";
                request.UserAgent =
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    + "Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0";
                response = (HttpWebResponse)request.GetResponse();
            }
            catch (WebException exception)
            {
                var bad = exception.Response as HttpWebResponse;
                if (bad != null)
                {
                    using (bad)
                    {
                        return Answer(new List<string> {
                            "The link does not work.",
                            "",
                            "The server answered " + (int)bad.StatusCode + ", " + bad.StatusDescription + ".",
                            sUrl });
                    }
                }
                return Answer(new List<string> {
                    "The link could not be reached.", "", exception.Message, sUrl });
            }
            catch (Exception exception)
            {
                return Answer(new List<string> {
                    "The link could not be reached.", "", exception.Message, sUrl });
            }

            try
            {
                string sFinalUrl = response.ResponseUri != null
                    ? response.ResponseUri.ToString() : sUrl;
                string sFinalHost = response.ResponseUri != null
                    ? response.ResponseUri.Host.ToLowerInvariant() : sHost;
                string sType = (response.ContentType ?? "").Split(';')[0].Trim().ToLowerInvariant();
                string sDisposition = response.Headers["Content-Disposition"] ?? "";

                // What kind of thing it is.
                string sWhat = dTypeNames.ContainsKey(sType)
                    ? dTypeNames[sType]
                    : (sType != "" ? sType : "something the server did not name");
                lLines.Add("A " + sWhat);

                string sSize = DescribeSize(response.ContentLength);
                if (sSize != "")
                    lLines.Add("about " + sSize);

                // A file that will be saved rather than shown.
                if (sDisposition.ToLowerInvariant().Contains("attachment"))
                {
                    Match match = Regex.Match(sDisposition,
                        "filename\\*?=(?:UTF-8'')?\"?([^\";]+)", RegexOptions.IgnoreCase);
                    if (match.Success)
                        lLines.Add("saved as " + Uri.UnescapeDataString(match.Groups[1].Value));
                }

                // Where it actually ends up.
                if (sFinalHost != "" && sFinalHost != sHost)
                {
                    lLines.Add("");
                    lLines.Add("It goes to " + sFinalHost + ", not " + sHost + ".");
                }
                foreach (string sShort in lShorteners)
                {
                    if (sHost == sShort)
                    {
                        lLines.Add("The link itself only redirects, so its address said nothing.");
                        break;
                    }
                }

                // For a page, what it is about.
                if (sType == "text/html")
                {
                    string sHtml = ReadSome(response);
                    string sTitle = FirstMatch(sHtml,
                        "<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"']([^\"']+)",
                        "<meta[^>]+name=[\"']twitter:title[\"'][^>]+content=[\"']([^\"']+)",
                        "<title[^>]*>(.*?)</title>");
                    string sDescription = FirstMatch(sHtml,
                        "<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']+)",
                        "<meta[^>]+property=[\"']og:description[\"'][^>]+content=[\"']([^\"']+)");
                    string sSite = FirstMatch(sHtml,
                        "<meta[^>]+property=[\"']og:site_name[\"'][^>]+content=[\"']([^\"']+)");
                    string sAuthor = FirstMatch(sHtml,
                        "<meta[^>]+name=[\"']author[\"'][^>]+content=[\"']([^\"']+)",
                        "<meta[^>]+property=[\"']article:author[\"'][^>]+content=[\"']([^\"']+)");
                    string sPublished = FirstMatch(sHtml,
                        "<meta[^>]+property=[\"']article:published_time[\"'][^>]+content=[\"']([^\"']+)",
                        "<time[^>]+datetime=[\"']([^\"']+)");
                    string sLanguage = FirstMatch(sHtml, "<html[^>]+lang=[\"']([^\"']+)");

                    lLines.Add("");
                    if (sTitle != "")
                        lLines.Add(sTitle);
                    if (sSite != "")
                        lLines.Add("on " + sSite);
                    if (sAuthor != "")
                        lLines.Add("by " + sAuthor);
                    if (sPublished != "")
                        lLines.Add("published " + (sPublished.Length > 10 ? sPublished.Substring(0, 10) : sPublished));
                    if (sDescription != "")
                    {
                        lLines.Add("");
                        lLines.Add(sDescription);
                    }

                    // A rough sense of length, from the visible text. Not exact,
                    // and does not need to be: the question is whether this is a
                    // paragraph or an hour.
                    string sBody = Regex.Replace(sHtml, "<(script|style)[^>]*>.*?</\\1>", " ",
                        RegexOptions.IgnoreCase | RegexOptions.Singleline);
                    sBody = Regex.Replace(sBody, "<[^>]+>", " ");
                    int iWords = Regex.Matches(sBody, "[A-Za-z']+").Count;
                    if (iWords > 200)
                    {
                        int iMinutes = Math.Max(1, (int)Math.Round(iWords / 220.0));
                        lLines.Add("");
                        lLines.Add("Roughly " + iWords + " words, about " + iMinutes + " minutes.");
                    }

                    // Whether reading it will mean signing in, which is worth
                    // knowing before following rather than after.
                    string sLower = sHtml.ToLowerInvariant();
                    foreach (string sWall in new[] {
                        "subscribe to continue", "subscribers only", "paywall",
                        "sign in to continue", "log in to continue",
                        "create a free account", "you have reached your article limit" })
                    {
                        if (sLower.Contains(sWall))
                        {
                            lLines.Add("");
                            lLines.Add("It looks as though reading it needs a subscription or an account.");
                            break;
                        }
                    }

                    if (sLanguage != "" && !sLanguage.ToLowerInvariant().StartsWith("en"))
                        lLines.Add("The page says it is in " + sLanguage + ".");

                    // Does the link say where it goes?
                    string sWords = Regex.Replace(sLinkText ?? "", @"\s+", " ").Trim().ToLowerInvariant();
                    if (sWords.Length > 8 && sTitle != "")
                    {
                        var setWords = new HashSet<string>();
                        foreach (Match m in Regex.Matches(sWords, "[a-z']{4,}"))
                            setWords.Add(m.Value);
                        var setTitle = new HashSet<string>();
                        foreach (Match m in Regex.Matches(sTitle.ToLowerInvariant(), "[a-z']{4,}"))
                            setTitle.Add(m.Value);
                        setWords.IntersectWith(setTitle);
                        if (setWords.Count == 0)
                        {
                            lLines.Add("");
                            lLines.Add("The link's words and the page's title have nothing in common.");
                        }
                    }
                }

                lLines.Add("");
                lLines.Add(sFinalUrl);
            }
            finally
            {
                try { response.Close(); } catch (Exception) { }
            }
            return Answer(lLines);
        }

        // As much of a page as its head needs, and no more.
        private static string ReadSome(HttpWebResponse response)
        {
            try
            {
                using (Stream stream = response.GetResponseStream())
                {
                    var bBuffer = new byte[iReadLimitBytes];
                    int iTotal = 0;
                    while (iTotal < bBuffer.Length)
                    {
                        int iRead = stream.Read(bBuffer, iTotal, bBuffer.Length - iTotal);
                        if (iRead <= 0)
                            break;
                        iTotal += iRead;
                    }
                    return new UTF8Encoding(false).GetString(bBuffer, 0, iTotal);
                }
            }
            catch (Exception)
            {
                return "";
            }
        }

        private static string Answer(List<string> lLines)
        {
            return "{\"value\":" + Quote(string.Join("\r\n", lLines.ToArray())) + "}";
        }

        // Puts a FILE on the clipboard, the way dragging it would, AND its path
        // as text on the same clipboard.
        //
        // Both formats, because a file drop attaches in Outlook and pastes as
        // nothing at all in a plain text box — the copy succeeded and the paste
        // produced an empty line. A data object carries several formats at
        // once, so Control+V now does something whichever window it is pressed
        // in.
        //
        // This lives here rather than in the scripts because the clipboard
        // needs a single threaded apartment, which a program declares and
        // PowerShell has to be told, failing into a hidden console when it is
        // not. Neither Windows Script Host nor the FileSystemObject can put a
        // file on the clipboard at all.
        /// <summary>
        /// What is actually on the clipboard, format by format.
        ///
        /// THE CLIPBOARD FAULT HAS SURVIVED THREE HYPOTHESES because every one
        /// of them was a guess about what FileDir wants, tested by asking a
        /// person to press a key and report a symptom. This turns it into a
        /// measurement: put a file on the clipboard with FileDir, ask this what
        /// is there; do the same with HomerView, ask again; the difference is
        /// the answer.
        ///
        /// The DropEffect is called out separately because it is the one format
        /// a reader can ask for and fail on when it is absent, and FileDir's
        /// clipboard2Path takes a bCut flag that has to come from somewhere.
        /// </summary>
        private static string ClipboardFormats()
        {
            try
            {
                var oData = System.Windows.Forms.Clipboard.GetDataObject();
                if (oData == null)
                    return "nothing at all";
                string[] lFormats = oData.GetFormats();
                if (lFormats == null || lFormats.Length == 0)
                    return "no formats";
                var oText = new StringBuilder();
                oText.Append(lFormats.Length.ToString());
                oText.Append(" formats: ");
                oText.Append(string.Join(", ", lFormats));
                if (System.Windows.Forms.Clipboard.ContainsFileDropList())
                {
                    var lDropped = System.Windows.Forms.Clipboard.GetFileDropList();
                    oText.Append(" | file drop holds ");
                    oText.Append(lDropped.Count.ToString());
                    if (lDropped.Count > 0)
                    {
                        oText.Append(": ");
                        oText.Append(lDropped[0]);
                    }
                }
                else
                {
                    oText.Append(" | NO FILE DROP");
                }
                oText.Append(System.Windows.Forms.Clipboard.ContainsText()
                    ? " | text present" : " | NO TEXT");
                oText.Append(oData.GetDataPresent("Preferred DropEffect")
                    ? " | DropEffect present" : " | NO DROPEFFECT");
                return oText.ToString();
            }
            catch (Exception oError)
            {
                return "could not be read: " + oError.Message;
            }
        }

        /// <summary>
        /// What is on the clipboard, said the way FileDir says it.
        ///
        /// FileDir's menuQueryClipboard announces "Path drop list" and then
        /// each path when there is a file drop, and otherwise reads the text.
        /// Answering the same question differently in two of his own programs
        /// would be a second vocabulary for one idea.
        /// </summary>
        private static string ClipboardSay()
        {
            try
            {
                if (System.Windows.Forms.Clipboard.ContainsFileDropList())
                {
                    var lDropped = System.Windows.Forms.Clipboard.GetFileDropList();
                    if (lDropped.Count > 0)
                    {
                        var oText = new StringBuilder();
                        oText.Append("Path drop list");
                        foreach (string sDropped in lDropped)
                        {
                            oText.Append("\r\n");
                            oText.Append(sDropped);
                        }
                        return "{\"value\":" + Quote(oText.ToString()) + "}";
                    }
                }
                if (System.Windows.Forms.Clipboard.ContainsText())
                    return "{\"value\":" + Quote(
                        System.Windows.Forms.Clipboard.GetText()) + "}";
                return "{\"error\":\"The clipboard is empty.\"}";
            }
            catch (Exception oError)
            {
                return "{\"error\":" + Quote(oError.Message) + "}";
            }
        }

        private static string ClipboardClear()
        {
            try
            {
                System.Windows.Forms.Clipboard.Clear();
                return "{\"value\":\"The clipboard is empty.\"}";
            }
            catch (Exception oError)
            {
                return "{\"error\":" + Quote(oError.Message) + "}";
            }
        }

        /// <summary>
        /// Writes the clipboard's text to a file, replacing or adding to it.
        /// The argument is the path; append is asked for by a leading plus.
        /// </summary>
        private static string ClipboardToFile(string sArgument)
        {
            bool bAppend = sArgument.StartsWith("+");
            string sPath = bAppend ? sArgument.Substring(1) : sArgument;
            if (string.IsNullOrEmpty(sPath))
                return "{\"error\":\"No file was named.\"}";
            try
            {
                if (!System.Windows.Forms.Clipboard.ContainsText())
                    return "{\"error\":\"There is no text on the clipboard to save.\"}";
                string sText = System.Windows.Forms.Clipboard.GetText();
                string sFolder = Path.GetDirectoryName(sPath);
                if (!string.IsNullOrEmpty(sFolder))
                    Directory.CreateDirectory(sFolder);
                if (bAppend)
                {
                    // A BLANK LINE BETWEEN ENTRIES. Without one an appended
                    // file runs together and the boundary between two things
                    // gathered at different moments is invisible. Only when
                    // there is something before it, so the file does not begin
                    // with an empty line.
                    string sLead = "";
                    if (File.Exists(sPath) && new FileInfo(sPath).Length > 0)
                        sLead = Environment.NewLine;
                    File.AppendAllText(sPath, sLead + sText + Environment.NewLine,
                        new UTF8Encoding(true));
                }
                else
                    File.WriteAllText(sPath, sText, new UTF8Encoding(true));
                var oInfo = new FileInfo(sPath);
                return "{\"value\":" + Quote((bAppend ? "Added to " : "Saved to ")
                    + sPath + ", now " + oInfo.Length.ToString() + " bytes.") + "}";
            }
            catch (Exception oError)
            {
                return "{\"error\":" + Quote(oError.Message) + "}";
            }
        }

        /// <summary>
        /// Adds text to what is already on the clipboard, rather than
        /// replacing it. JSL has CopyToClipboard, which erases first, and no
        /// way to read the clipboard at all, so the append has to happen here.
        /// </summary>
        private static string ClipboardAdd(string sText)
        {
            if (string.IsNullOrEmpty(sText))
                return "{\"error\":\"There was nothing to add.\"}";
            try
            {
                string sExisting = System.Windows.Forms.Clipboard.ContainsText()
                    ? System.Windows.Forms.Clipboard.GetText() : "";
                string sJoined = sExisting == ""
                    ? sText : sExisting.TrimEnd() + Environment.NewLine + sText;
                System.Windows.Forms.Clipboard.SetText(sJoined);
                Log("  clipboard now holds: " + ClipboardFormats());
                return "{\"value\":" + Quote("Added. The clipboard now holds "
                    + sJoined.Length.ToString() + " characters.") + "}";
            }
            catch (Exception oError)
            {
                return "{\"error\":" + Quote(oError.Message) + "}";
            }
        }

        /// <summary>
        /// A folder under Downloads named after the page, emptied first.
        ///
        /// HIS RULE, and it is a better one than numbering files: an analysis
        /// produces several files that belong together, so they go in a folder
        /// of their own named for the page, and running it again REPLACES that
        /// folder entirely. Numbered duplicates in one flat Downloads folder
        /// leave you guessing which run a file came from.
        ///
        /// The name is sanitised the same way exportReport.py does it on the
        /// NVDA side -- the characters Windows forbids removed, runs of white
        /// space collapsed, seventy characters kept -- so the two halves of one
        /// program name a folder identically.
        /// </summary>
        /// <summary>
        /// A page title turned into a name Windows will actually accept.
        ///
        /// PORTED FROM urlFido's folderNameFromTitle, which follows urlCheck's
        /// rules, because MY VERSION HAD TWO LATENT FAULTS and both are the
        /// kind that fire on one page in a hundred and look like nothing else:
        ///
        ///   - A TRAILING DOT OR SPACE is illegal at the end of a Windows name.
        ///     A page titled "Contact us." would have produced a path the
        ///     system refuses, and the failure would have arrived as an
        ///     exception message about an unrelated-looking path.
        ///   - A RESERVED DEVICE NAME cannot be a file or folder at all. A page
        ///     titled "Aux" or "Con" is uncreatable, so an underscore is put in
        ///     front to defang it.
        ///
        /// The other decisions are urlCheck's and worth keeping: original
        /// capitalisation and the spaces between words are PRESERVED rather
        /// than flattened into dashes, because the name is read by a person
        /// browsing Downloads. "Home | American Foundation for the Blind"
        /// reads better than "home-american-foundation".
        /// </summary>
        private static string SafeStem(string sPageTitle)
        {
            string sName = (sPageTitle ?? "").Trim();
            if (sName.Length == 0) sName = "report";
            sName = Regex.Replace(sName, "[<>:\"/\\\\|?*\\x00-\\x1f]", "");
            sName = Regex.Replace(sName, "\\s+", " ").Trim();
            while (sName.EndsWith(".") || sName.EndsWith(" "))
                sName = sName.Substring(0, sName.Length - 1);
            string sCheck = sName.ToUpperInvariant().Split('.')[0];
            foreach (string sReserved in new string[] {
                "CON", "PRN", "AUX", "NUL",
                "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9" })
            {
                if (sCheck == sReserved) { sName = "_" + sName; break; }
            }
            if (sName.Length == 0) sName = "report";
            if (sName.Length > 70) sName = sName.Substring(0, 70);
            while (sName.EndsWith(".") || sName.EndsWith(" "))
                sName = sName.Substring(0, sName.Length - 1);
            if (sName.Length == 0) sName = "report";
            return sName;
        }

        private static string DownloadsFolder()
        {
            string sDownloads = null;
            try
            {
                sDownloads = (string) Microsoft.Win32.Registry.GetValue(
                    "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders",
                    "{374DE290-123F-4565-9164-39C4925E467B}", null);
            }
            catch { }
            if (string.IsNullOrEmpty(sDownloads) || !Directory.Exists(sDownloads))
                sDownloads = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    "Downloads");
            return sDownloads;
        }

        private static string ExportFolder(string sPageTitle)
        {
            // A SUFFIX, BECAUSE THIS FOLDER IS EMPTIED AND THE DOWNLOAD FOLDER
            // IS NOT.
            //
            // Both were named Downloads\<page title>, and this one deletes
            // whatever is there before writing. On 14 August seventeen files,
            // 3.8 megabytes, were downloaded from an FCC page and then DELETED
            // sixty seconds later by an accessibility run on the same page.
            // Two features that write to one place, one of which clears it,
            // was a data-loss fault waiting for the day somebody used both.
            string sFolder = Path.Combine(DownloadsFolder(),
                SafeStem(sPageTitle) + " - accessibility");
            // Replaced, not added to: a folder half from this run and half from
            // the last is worse than either.
            if (Directory.Exists(sFolder))
            {
                try { Directory.Delete(sFolder, true); }
                catch (Exception oError)
                {
                    Log("  the old folder could not be removed: " + oError.Message);
                }
            }
            Directory.CreateDirectory(sFolder);
            Log("  results folder: " + sFolder);
            return sFolder;
        }

        /// <summary>
        /// Opens a page or a local file in HOMERVIEW'S Edge, not the default
        /// browser.
        ///
        /// The guide used to be opened with cmd /c start, which asks Windows
        /// which program handles .htm. On a machine whose default browser is
        /// Firefox, the HomerView guide opened in Firefox — where not one
        /// HomerView command works, because there is no debugging connection
        /// to it. Anything HomerView opens belongs in HomerView's browser.
        ///
        /// A local path is turned into a file address first, because
        /// Target.createTarget wants a URL.
        /// </summary>
        private static string OpenPage(string sTarget)
        {
            if (string.IsNullOrEmpty(sTarget))
                return "{\"error\":\"Nothing was named to open.\"}";
            string sUrl = sTarget;
            if (!sUrl.Contains("://"))
            {
                if (!File.Exists(sUrl) && !Directory.Exists(sUrl))
                    return "{\"error\":" + Quote("There is nothing at " + sUrl) + "}";
                sUrl = new Uri(Path.GetFullPath(sUrl)).AbsoluteUri;
            }
            if (!ReadPort())
                return "{\"error\":\"HomerView's browser is not running. Press the launch key first.\"}";
            string sOutcome = OpenInTab(sUrl);
            if (sOutcome.StartsWith("but"))
                return "{\"error\":\"The page could not be opened in HomerView's browser.\"}";
            return "{\"value\":" + Quote("Opened in HomerView: " + sUrl) + "}";
        }

        /// <summary>
        /// Every word on the page, for Copy All.
        /// </summary>
        private static string CopyAllText()
        {
            string sText = PageText();
            if (sText == null || sText == "" || sText.StartsWith("ERROR:"))
                return "{\"error\":\"The page's text could not be read.\"}";
            try
            {
                System.Windows.Forms.Clipboard.SetText(sText);
                Log("  clipboard now holds: " + ClipboardFormats());
                return "{\"value\":" + Quote("The whole page is on the clipboard, "
                    + sText.Length.ToString() + " characters.") + "}";
            }
            catch (Exception oError)
            {
                return "{\"error\":" + Quote(oError.Message) + "}";
            }
        }

        // --- The page's own text, and the IBM Equal Access engine ------------

        /// <summary>
        /// THE TEXT OF THE PAGE AS THE BROWSER HAS IT, which is what Control+A
        /// would select — not the virtual view.
        ///
        /// His distinction, and it decides both Copy All and Read All. JAWS's
        /// Say All speaks the VIRTUAL view from the CURSOR onward: close to the
        /// page but not the same, since the virtual view puts a link on a line
        /// of its own among other differences, and it starts wherever the
        /// reader happens to be. Copy All and Read All both take the whole
        /// document from the top, from the DOM, so the two halves of HomerView
        /// and the two screen readers all deliver the same characters.
        /// </summary>
        private static string PageText()
        {
            return EvaluateText(
                "(() => (document.body ? document.body.innerText : \"\"))()");
        }

        private const string sAxeCacheName = "axe.min.js";
        private static readonly string[] lAxeUrls = new string[] {
            "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js",
            "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js",
            "https://unpkg.com/axe-core@4.10.2/axe.min.js" };

        /// <summary>
        /// Fetches an engine once, caches it, and injects it AS SOURCE TEXT.
        ///
        /// WHY THIS EXISTS: the axe command used to build a script element in
        /// the page and point it at a content delivery network. That works on a
        /// file:// page, which has no content security policy, and fails on a
        /// real site that has one — which is why "The testing engine could not
        /// be loaded" appeared on searx.space and never on HomerView's own
        /// start page. The failure looked like a HomerView fault and was a
        /// policy doing its job.
        ///
        /// Injected through Runtime.evaluate the source arrives in the page's
        /// own context through the debugger, so no policy is consulted at all.
        /// Readability and the IBM engine already came in this way; axe was the
        /// last one still knocking at the front door.
        /// </summary>
        private static bool InjectEngine(string sCacheName, string[] lUrls,
            string sPresentTest, int iSmallest)
        {
            if (EvaluateText(sPresentTest) == "yes")
                return true;
            string sCache = Path.Combine(
                Directory.GetParent(ProfileFolder()).FullName, "cache", sCacheName);
            string sSource = "";
            try
            {
                if (File.Exists(sCache) && new FileInfo(sCache).Length > iSmallest)
                    sSource = File.ReadAllText(sCache);
            }
            catch (Exception) { }
            if (sSource == "")
            {
                foreach (string sUrl in lUrls)
                {
                    try
                    {
                        ServicePointManager.SecurityProtocol =
                            SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11 | SecurityProtocolType.Tls;
                        var request = (HttpWebRequest)WebRequest.Create(sUrl);
                        request.Timeout = 45000;
                        request.UserAgent = "HomerView";
                        using (var response = (HttpWebResponse)request.GetResponse())
                        using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
                        {
                            string sFetched = reader.ReadToEnd();
                            if (sFetched.Length > iSmallest)
                            {
                                sSource = sFetched;
                                try
                                {
                                    Directory.CreateDirectory(Path.GetDirectoryName(sCache));
                                    File.WriteAllText(sCache, sSource, new UTF8Encoding(false));
                                }
                                catch (Exception) { }
                                Log("  fetched " + sCacheName + " from " + sUrl + ", "
                                    + sSource.Length.ToString() + " characters");
                                break;
                            }
                        }
                    }
                    catch (Exception oError)
                    {
                        Log("  " + sCacheName + " from " + sUrl + " failed: " + oError.Message);
                    }
                }
            }
            if (sSource == "")
                return false;
            EvaluateText(sSource);
            bool bReady = EvaluateText(sPresentTest) == "yes";
            Log("  " + sCacheName + (bReady ? " is loaded in the page" : " did NOT load"));
            return bReady;
        }

        private const string sAxePresent =
            "(() => (typeof axe !== \"undefined\" && !!axe.run) ? \"yes\" : \"no\")()";

        private const string sAceCacheName = "ace.js";
        private static readonly string[] lAceUrls = new string[] {
            "https://unpkg.com/accessibility-checker-engine@latest/ace.js",
            "https://cdn.jsdelivr.net/npm/accessibility-checker-engine@latest/ace.js",
            "https://able.ibm.com/rules/archives/latest/js/ace.js" };

        // The engine reports a level and an outcome as a pair, and turning that
        // into words a reader can act on is most of the work. Same table as
        // ace.py on the NVDA side, so the two report identically.
        private static string AceBucket(string sLevel, string sOutcome)
        {
            string sKey = sLevel + "|" + sOutcome;
            if (sKey == "VIOLATION|FAIL") return "violation";
            if (sKey == "VIOLATION|POTENTIAL") return "needs review";
            if (sKey == "RECOMMENDATION|FAIL") return "recommendation";
            if (sKey == "RECOMMENDATION|POTENTIAL") return "needs review";
            if (sKey == "INFORMATION|MANUAL") return "manual check";
            if (sOutcome == "PASS") return "pass";
            return "other";
        }

        private static string Tidy(string sText)
        {
            if (sText == null) return "";
            return Regex.Replace(sText, "\\s+", " ").Trim();
        }

        private static string EscapeXmlText(string sText)
        {
            return (sText ?? "").Replace("&", "&amp;").Replace("<", "&lt;")
                .Replace(">", "&gt;").Replace("\"", "&quot;").Replace("'", "&apos;");
        }

        private static string ColumnName(int iIndex)
        {
            string sName = "";
            while (iIndex > 0)
            {
                int iRemainder = (iIndex - 1) % 26;
                iIndex = (iIndex - 1) / 26;
                sName = ((char)(65 + iRemainder)).ToString() + sName;
            }
            return sName;
        }

        private static string SheetXml(List<string[]> lRows)
        {
            var oText = new StringBuilder();
            oText.Append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>");
            oText.Append("<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>");
            for (int iRow = 1; iRow <= lRows.Count; iRow++)
            {
                oText.Append("<row r=\"" + iRow.ToString() + "\">");
                string[] lRow = lRows[iRow - 1];
                for (int iColumn = 1; iColumn <= lRow.Length; iColumn++)
                {
                    string sCell = lRow[iColumn - 1] ?? "";
                    if (sCell.Length > 32000) sCell = sCell.Substring(0, 32000);
                    oText.Append("<c r=\"" + ColumnName(iColumn) + iRow.ToString()
                        + "\" t=\"inlineStr\"><is><t xml:space=\"preserve\">");
                    oText.Append(EscapeXmlText(sCell));
                    oText.Append("</t></is></c>");
                }
                oText.Append("</row>");
            }
            oText.Append("</sheetData></worksheet>");
            return oText.ToString();
        }

        /// <summary>
        /// A workbook, written by hand as a zip of XML.
        ///
        /// The same approach exportReport.py takes on the NVDA side, and for
        /// the same reason: an .xlsx is a zip of XML parts, so writing one
        /// needs no library and adds no dependency to a program that must run
        /// from a folder anywhere.
        /// </summary>
        private static void WriteXlsx(string sPath, List<KeyValuePair<string, List<string[]>>> lSheets)
        {
            using (var oFile = new FileStream(sPath, FileMode.Create, FileAccess.Write))
            using (var oZip = new System.IO.Compression.ZipArchive(
                oFile, System.IO.Compression.ZipArchiveMode.Create))
            {
                var oOverrides = new StringBuilder();
                var oWorkbookSheets = new StringBuilder();
                var oRelationships = new StringBuilder();
                for (int i = 1; i <= lSheets.Count; i++)
                {
                    oOverrides.Append("<Override PartName=\"/xl/worksheets/sheet" + i.ToString()
                        + ".xml\" ContentType=\"application/vnd.openxmlformats-officedocument."
                        + "spreadsheetml.worksheet+xml\"/>");
                    string sName = EscapeXmlText(lSheets[i - 1].Key);
                    if (sName.Length > 31) sName = sName.Substring(0, 31);
                    oWorkbookSheets.Append("<sheet name=\"" + sName + "\" sheetId=\"" + i.ToString()
                        + "\" r:id=\"rId" + i.ToString() + "\"/>");
                    oRelationships.Append("<Relationship Id=\"rId" + i.ToString()
                        + "\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/"
                        + "relationships/worksheet\" Target=\"worksheets/sheet" + i.ToString() + ".xml\"/>");
                }
                WriteZipEntry(oZip, "[Content_Types].xml",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
                    + "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
                    + "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
                    + "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
                    + oOverrides.ToString() + "</Types>");
                WriteZipEntry(oZip, "_rels/.rels",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                    + "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>"
                    + "</Relationships>");
                WriteZipEntry(oZip, "xl/workbook.xml",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
                    + "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
                    + "<sheets>" + oWorkbookSheets.ToString() + "</sheets></workbook>");
                WriteZipEntry(oZip, "xl/_rels/workbook.xml.rels",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                    + oRelationships.ToString() + "</Relationships>");
                for (int i = 1; i <= lSheets.Count; i++)
                    WriteZipEntry(oZip, "xl/worksheets/sheet" + i.ToString() + ".xml",
                        SheetXml(lSheets[i - 1].Value));
            }
        }

        private static void WriteZipEntry(System.IO.Compression.ZipArchive oZip,
            string sName, string sContent)
        {
            var oEntry = oZip.CreateEntry(sName);
            using (var oStream = oEntry.Open())
            using (var oWriter = new StreamWriter(oStream, new UTF8Encoding(false)))
                oWriter.Write(sContent);
        }

        private static string CsvCell(string sText)
        {
            string sCell = sText ?? "";
            if (sCell.IndexOfAny(new char[] { ',', '"', '\r', '\n' }) < 0)
                return sCell;
            return "\"" + sCell.Replace("\"", "\"\"") + "\"";
        }

        private static void WriteCsv(string sPath, List<string[]> lRows)
        {
            var oText = new StringBuilder();
            foreach (string[] lRow in lRows)
            {
                var lCells = new List<string>();
                foreach (string sCell in lRow) lCells.Add(CsvCell(sCell));
                oText.Append(string.Join(",", lCells.ToArray()));
                oText.Append("\r\n");
            }
            // A byte order mark, because Excel reads a CSV without one as ANSI
            // and turns every accented character into rubbish.
            File.WriteAllText(sPath, oText.ToString(), new UTF8Encoding(true));
        }

        /// <summary>
        /// Runs IBM Equal Access on the focused page and saves every format.
        ///
        /// The folder is his rule: a subdirectory of Downloads named after the
        /// page, replaced wholesale each run, holding the files that belong
        /// together. The HTML report is opened in HomerView's own browser when
        /// it is done, because that is where every other HomerView command
        /// works.
        /// </summary>
        private static string Ace(string sRuleset)
        {
            if (string.IsNullOrEmpty(sRuleset)) sRuleset = "IBM_Accessibility";
            if (!InjectEngine(sAceCacheName, lAceUrls,
                "(() => (typeof ace !== \"undefined\" && !!ace.Checker) ? \"yes\" : \"no\")()",
                100000))
                return "{\"error\":\"The IBM Equal Access engine could not be loaded. Check the internet connection.\"}";

            string sTitle = Tidy(EvaluateText("(() => document.title)()"));
            string sUrl = Tidy(EvaluateText("(() => location.href)()"));
            if (sTitle == "" || sTitle.StartsWith("ERROR:")) sTitle = sUrl;

            // THE REPORT IS REDUCED IN THE BROWSER, NOT SHIPPED WHOLE.
            //
            // This is why the command appeared to hang. It used to evaluate
            // JSON.stringify(report) and bring back the ENTIRE IBM report --
            // every passing result included, which on a large page is tens of
            // thousands of entries and many megabytes. That payload then went
            // through JsonToXml into an XmlDocument, which builds a DOM node
            // for every value in it. The browser was not slow; the parse was,
            // and on a big enough page it would not finish at all.
            //
            // The axe path never had this problem because it already reduces
            // in the browser: it returns the violations and a COUNT of the
            // passes. This now does the same. What comes back is one line per
            // finding and a count of the rest, so the payload is proportional
            // to what a person will read rather than to what the engine
            // examined. No JSON parsing is needed at all on this path.
            //
            // The old code also had NO logging between starting the run and
            // finishing it, so the log could not say which step had stalled.
            // Every step now says what it did and how long it took.
            Log("  IBM engine ready, running the " + sRuleset + " ruleset");
            DateTime oStarted = DateTime.UtcNow;
            int iWas = iCallBudgetSeconds;
            iCallBudgetSeconds = 120;

            string sReport = EvaluateText(
                "(async () => {"
                + " const checker = new ace.Checker();"
                + " const report = await checker.check(document, [\"" + sRuleset + "\"]);"
                + " const lResults = report.results || [];"
                + " let iPass = 0;"
                + " const lRows = [];"
                + " for (const r of lResults) {"
                + "   const v = r.value || [];"
                + "   const sLevel = String(v[0] || ''), sOutcome = String(v[1] || '');"
                + "   if (sOutcome === 'PASS') { iPass += 1; continue; }"
                + "   const p = r.path || {};"
                + "   lRows.push([sLevel, sOutcome, String(r.ruleId || ''),"
                + "     String(r.message || '').replace(/\\s+/g, ' ').trim(),"
                + "     String(p.dom || p.aria || ''),"
                + "     String(r.snippet || '').replace(/\\s+/g, ' ').trim().slice(0, 400)"
                + "     ].join('\\u0001'));"
                + " }"
                + " return iPass + '\\u0002' + lResults.length + '\\u0002' + lRows.join('\\n');"
                + "})()");
            iCallBudgetSeconds = iWas;
            Log("  the engine answered "
                + (sReport == null ? "nothing" : sReport.Length.ToString() + " characters")
                + " after " + ((int) (DateTime.UtcNow - oStarted).TotalSeconds).ToString()
                + " seconds");
            if (sReport == null || sReport == "" || sReport.StartsWith("ERROR:"))
                return "{\"error\":" + Quote("The IBM engine did not finish on this page. "
                    + Abbreviate(sReport, 200)) + "}";

            string[] lHead = sReport.Split('\u0002');
            if (lHead.Length < 3)
                return "{\"error\":\"The IBM engine's answer was not in the expected shape.\"}";
            int iPassed = 0;
            int.TryParse(lHead[0], out iPassed);

            var lRows = new List<string[]>();
            lRows.Add(new string[] { "Kind", "Rule", "Message", "Path", "Snippet" });
            var dBuckets = new Dictionary<string, List<string[]>>();
            var dCounts = new Dictionary<string, int>();
            foreach (string sName in new string[] {
                "violation", "needs review", "recommendation", "manual check", "pass", "other" })
            {
                dBuckets[sName] = new List<string[]>();
                dCounts[sName] = 0;
            }
            dCounts["pass"] = iPassed;

            foreach (string sLine in lHead[2].Split('\n'))
            {
                if (sLine.Trim() == "") continue;
                string[] lField = sLine.Split('\u0001');
                if (lField.Length < 6) continue;
                string sBucket = AceBucket(lField[0], lField[1]);
                if (sBucket == "pass") { dCounts["pass"] = dCounts["pass"] + 1; continue; }
                dCounts[sBucket] = dCounts[sBucket] + 1;
                dBuckets[sBucket].Add(new string[] {
                    sBucket, lField[2], lField[3], lField[4], lField[5] });
            }
            Log("  " + dCounts["violation"].ToString() + " violations, "
                + dCounts["needs review"].ToString() + " to review, "
                + dCounts["recommendation"].ToString() + " recommendations, "
                + dCounts["manual check"].ToString() + " manual, "
                + dCounts["pass"].ToString() + " passed");

            foreach (string sName in new string[] {
                "violation", "needs review", "recommendation", "manual check" })
                foreach (string[] lRow in dBuckets[sName]) lRows.Add(lRow);

            var lSheets = new List<KeyValuePair<string, List<string[]>>>();
            var lSummary = new List<string[]>();
            lSummary.Add(new string[] { "Page", sTitle });
            lSummary.Add(new string[] { "Address", sUrl });
            lSummary.Add(new string[] { "Ruleset", sRuleset });
            lSummary.Add(new string[] { "Tested", DateTime.Now.ToString("yyyy-MM-dd HH:mm") });
            lSummary.Add(new string[] { "", "" });
            foreach (string sName in new string[] {
                "violation", "needs review", "recommendation", "manual check", "pass" })
                lSummary.Add(new string[] { sName, dCounts[sName].ToString() });
            lSheets.Add(new KeyValuePair<string, List<string[]>>("Summary", lSummary));
            foreach (string sName in new string[] {
                "violation", "needs review", "recommendation", "manual check" })
            {
                if (dBuckets[sName].Count == 0) continue;
                var lSheetRows = new List<string[]>();
                lSheetRows.Add(new string[] { "Rule", "Message", "Path", "Snippet" });
                foreach (string[] lRow in dBuckets[sName])
                    lSheetRows.Add(new string[] { lRow[1], lRow[2], lRow[3], lRow[4] });
                string sSheetName = sName.Substring(0, 1).ToUpper() + sName.Substring(1);
                lSheets.Add(new KeyValuePair<string, List<string[]>>(sSheetName, lSheetRows));
            }

            string sFolder = ExportFolder(sTitle);
            var lWritten = new List<string>();
            string sHtmlPath = Path.Combine(sFolder, "Report.htm");
            try
            {
                // BUILT FROM THE ROWS, not from the engine's own output.
                // Shipping the whole report back is what made this command
                // appear to hang, so the json here is the same findings the
                // other three formats hold, written as json.
                var oJson = new StringBuilder();
                oJson.Append("{\"page\":" + Quote(sTitle) + ",");
                oJson.Append("\"address\":" + Quote(sUrl) + ",");
                oJson.Append("\"ruleset\":" + Quote(sRuleset) + ",");
                oJson.Append("\"counts\":{");
                bool bFirst = true;
                foreach (string sName in new string[] {
                    "violation", "needs review", "recommendation", "manual check", "pass" })
                {
                    if (!bFirst) oJson.Append(",");
                    bFirst = false;
                    oJson.Append(Quote(sName) + ":" + dCounts[sName].ToString());
                }
                oJson.Append("},\"findings\":[");
                bFirst = true;
                for (int i = 1; i < lRows.Count; i++)
                {
                    if (!bFirst) oJson.Append(",");
                    bFirst = false;
                    oJson.Append("{\"kind\":" + Quote(lRows[i][0])
                        + ",\"rule\":" + Quote(lRows[i][1])
                        + ",\"message\":" + Quote(lRows[i][2])
                        + ",\"path\":" + Quote(lRows[i][3])
                        + ",\"snippet\":" + Quote(lRows[i][4]) + "}");
                }
                oJson.Append("]}");
                File.WriteAllText(Path.Combine(sFolder, "Report.json"),
                    oJson.ToString(), new UTF8Encoding(true));
                lWritten.Add("Report.json");
            }
            catch (Exception oError) { Log("  json failed: " + oError.Message); }
            try
            {
                WriteCsv(Path.Combine(sFolder, "Report.csv"), lRows);
                lWritten.Add("Report.csv");
                Log("  wrote Report.csv");
            }
            catch (Exception oError) { Log("  csv failed: " + oError.Message); }
            try
            {
                WriteXlsx(Path.Combine(sFolder, "Report.xlsx"), lSheets);
                lWritten.Add("Report.xlsx");
                Log("  wrote Report.xlsx");
            }
            catch (Exception oError) { Log("  xlsx failed: " + oError.Message); }
            try
            {
                File.WriteAllText(sHtmlPath,
                    AceHtml(sTitle, sUrl, sRuleset, dCounts, dBuckets), new UTF8Encoding(true));
                lWritten.Add("Report.htm");
                Log("  wrote Report.htm");
            }
            catch (Exception oError) { Log("  html failed: " + oError.Message); }

            string sOpened = "";
            if (File.Exists(sHtmlPath))
                sOpened = OpenInTab(new Uri(sHtmlPath).AbsoluteUri);

            // ONE SENTENCE, SPOKEN, BECAUSE THE REPORT IS THE ANSWER.
            //
            // This used to return a multi-line summary, which sayOrShow quite
            // correctly put in the Virtual Viewer -- and the viewer takes
            // focus, so the report that had just been opened in a tab was
            // sitting behind a buffer repeating what it says. The detail
            // belongs in the report; what is spoken is only enough to know it
            // worked and roughly what was found.
            var oAnswer = new StringBuilder();
            oAnswer.Append(dCounts["violation"].ToString() + " violations, ");
            oAnswer.Append(dCounts["needs review"].ToString() + " to review, ");
            oAnswer.Append(dCounts["recommendation"].ToString() + " recommendations, ");
            oAnswer.Append(dCounts["pass"].ToString() + " passed. ");
            oAnswer.Append(lWritten.Count.ToString() + " files in Downloads, ");
            oAnswer.Append(Path.GetFileName(sFolder) + ". ");
            oAnswer.Append(sOpened == "" ? "The report was not opened."
                : "The report is " + sOpened);
            return "{\"value\":" + Quote(oAnswer.ToString()) + "}";
        }

        private static string EscapeJson(string sText)
        {
            return (sText ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"")
                .Replace("\r", " ").Replace("\n", " ");
        }

        private static string AceHtml(string sTitle, string sUrl, string sRuleset,
            Dictionary<string, int> dCounts, Dictionary<string, List<string[]>> dBuckets)
        {
            var oText = new StringBuilder();
            oText.Append("<!DOCTYPE html>\r\n<html lang=\"en\">\r\n<head>\r\n");
            oText.Append("<meta charset=\"utf-8\">\r\n<title>Accessibility report: ");
            oText.Append(EscapeHtml(sTitle));
            oText.Append("</title>\r\n</head>\r\n<body>\r\n");
            oText.Append("<h1>Accessibility report</h1>\r\n");
            oText.Append("<p><a href=\"#findings\">Skip to the findings</a></p>\r\n");
            oText.Append("<h2>What was tested</h2>\r\n<ul>\r\n");
            oText.Append("<li>Page: " + EscapeHtml(sTitle) + "</li>\r\n");
            oText.Append("<li>Address: <a href=\"" + EscapeHtml(sUrl) + "\">"
                + EscapeHtml(sUrl) + "</a></li>\r\n");
            oText.Append("<li>Engine: IBM Equal Access, ruleset " + EscapeHtml(sRuleset)
                + ", which folds EN 301 549 and Section 508 in with WCAG</li>\r\n");
            oText.Append("<li>Tested: " + DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "</li>\r\n");
            oText.Append("</ul>\r\n<h2>How much was found</h2>\r\n<ul>\r\n");
            oText.Append("<li>" + dCounts["violation"].ToString()
                + " violations, confirmed failures that need fixing</li>\r\n");
            oText.Append("<li>" + dCounts["needs review"].ToString()
                + " that need review, where a person has to judge</li>\r\n");
            oText.Append("<li>" + dCounts["recommendation"].ToString()
                + " recommendations, not failures but worth improving</li>\r\n");
            oText.Append("<li>" + dCounts["manual check"].ToString()
                + " manual checks, which the engine cannot decide at all</li>\r\n");
            oText.Append("<li>" + dCounts["pass"].ToString() + " passed</li>\r\n</ul>\r\n");
            oText.Append("<h2 id=\"findings\">Findings</h2>\r\n");
            bool bAny = false;
            foreach (string sName in new string[] {
                "violation", "needs review", "recommendation", "manual check" })
            {
                if (dBuckets[sName].Count == 0) continue;
                bAny = true;
                oText.Append("<h3>" + EscapeHtml(sName) + " ("
                    + dBuckets[sName].Count.ToString() + ")</h3>\r\n");
                foreach (string[] lRow in dBuckets[sName])
                {
                    oText.Append("<h4>" + EscapeHtml(lRow[1]) + "</h4>\r\n");
                    oText.Append("<p>" + EscapeHtml(lRow[2]) + "</p>\r\n<ul>\r\n");
                    oText.Append("<li>Where: <code>" + EscapeHtml(lRow[3]) + "</code></li>\r\n");
                    if (lRow[4] != "")
                        oText.Append("<li>Element: <code>" + EscapeHtml(lRow[4]) + "</code></li>\r\n");
                    oText.Append("</ul>\r\n");
                }
            }
            if (!bAny)
                oText.Append("<p>Nothing was found that needs attention.</p>\r\n");
            oText.Append("</body>\r\n</html>\r\n");
            return oText.ToString();
        }

        // --- The axe report, saved and opened ------------------------------

        /// <summary>
        /// Every WCAG success criterion axe can name, with its short name,
        /// conformance level and principle.
        ///
        /// Transcribed mechanically from wcag.py rather than retyped, because a
        /// wrong criterion name in a report is worse than no name: it looks
        /// authoritative and sends a publisher to the wrong place. axe tags a
        /// violation "wcag111" and this turns that into "1.1.1 Non-text
        /// Content, Level A, Perceivable".
        /// </summary>
        private static Dictionary<string, string[]> WcagTable()
        {
            var dWcag = new Dictionary<string, string[]>();
            dWcag["1.1.1"] = new string[] { "Non-text Content", "A", "Perceivable" };
            dWcag["1.2.1"] = new string[] { "Audio-only and Video-only (Prerecorded)", "A", "Perceivable" };
            dWcag["1.2.2"] = new string[] { "Captions (Prerecorded)", "A", "Perceivable" };
            dWcag["1.2.3"] = new string[] { "Audio Description or Media Alternative", "A", "Perceivable" };
            dWcag["1.2.4"] = new string[] { "Captions (Live)", "AA", "Perceivable" };
            dWcag["1.2.5"] = new string[] { "Audio Description (Prerecorded)", "AA", "Perceivable" };
            dWcag["1.2.6"] = new string[] { "Sign Language (Prerecorded)", "AAA", "Perceivable" };
            dWcag["1.2.7"] = new string[] { "Extended Audio Description (Prerecorded)", "AAA", "Perceivable" };
            dWcag["1.2.8"] = new string[] { "Media Alternative (Prerecorded)", "AAA", "Perceivable" };
            dWcag["1.2.9"] = new string[] { "Audio-only (Live)", "AAA", "Perceivable" };
            dWcag["1.3.1"] = new string[] { "Info and Relationships", "A", "Perceivable" };
            dWcag["1.3.2"] = new string[] { "Meaningful Sequence", "A", "Perceivable" };
            dWcag["1.3.3"] = new string[] { "Sensory Characteristics", "A", "Perceivable" };
            dWcag["1.3.4"] = new string[] { "Orientation", "AA", "Perceivable" };
            dWcag["1.3.5"] = new string[] { "Identify Input Purpose", "AA", "Perceivable" };
            dWcag["1.3.6"] = new string[] { "Identify Purpose", "AAA", "Perceivable" };
            dWcag["1.4.1"] = new string[] { "Use of Color", "A", "Perceivable" };
            dWcag["1.4.2"] = new string[] { "Audio Control", "A", "Perceivable" };
            dWcag["1.4.3"] = new string[] { "Contrast (Minimum)", "AA", "Perceivable" };
            dWcag["1.4.4"] = new string[] { "Resize Text", "AA", "Perceivable" };
            dWcag["1.4.5"] = new string[] { "Images of Text", "AA", "Perceivable" };
            dWcag["1.4.6"] = new string[] { "Contrast (Enhanced)", "AAA", "Perceivable" };
            dWcag["1.4.7"] = new string[] { "Low or No Background Audio", "AAA", "Perceivable" };
            dWcag["1.4.8"] = new string[] { "Visual Presentation", "AAA", "Perceivable" };
            dWcag["1.4.9"] = new string[] { "Images of Text (No Exception)", "AAA", "Perceivable" };
            dWcag["1.4.10"] = new string[] { "Reflow", "AA", "Perceivable" };
            dWcag["1.4.11"] = new string[] { "Non-text Contrast", "AA", "Perceivable" };
            dWcag["1.4.12"] = new string[] { "Text Spacing", "AA", "Perceivable" };
            dWcag["1.4.13"] = new string[] { "Content on Hover or Focus", "AA", "Perceivable" };
            dWcag["2.1.1"] = new string[] { "Keyboard", "A", "Operable" };
            dWcag["2.1.2"] = new string[] { "No Keyboard Trap", "A", "Operable" };
            dWcag["2.1.3"] = new string[] { "Keyboard (No Exception)", "AAA", "Operable" };
            dWcag["2.1.4"] = new string[] { "Character Key Shortcuts", "A", "Operable" };
            dWcag["2.2.1"] = new string[] { "Timing Adjustable", "A", "Operable" };
            dWcag["2.2.2"] = new string[] { "Pause, Stop, Hide", "A", "Operable" };
            dWcag["2.2.3"] = new string[] { "No Timing", "AAA", "Operable" };
            dWcag["2.2.4"] = new string[] { "Interruptions", "AAA", "Operable" };
            dWcag["2.2.5"] = new string[] { "Re-authenticating", "AAA", "Operable" };
            dWcag["2.2.6"] = new string[] { "Timeouts", "AAA", "Operable" };
            dWcag["2.3.1"] = new string[] { "Three Flashes or Below Threshold", "A", "Operable" };
            dWcag["2.3.2"] = new string[] { "Three Flashes", "AAA", "Operable" };
            dWcag["2.3.3"] = new string[] { "Animation from Interactions", "AAA", "Operable" };
            dWcag["2.4.1"] = new string[] { "Bypass Blocks", "A", "Operable" };
            dWcag["2.4.2"] = new string[] { "Page Titled", "A", "Operable" };
            dWcag["2.4.3"] = new string[] { "Focus Order", "A", "Operable" };
            dWcag["2.4.4"] = new string[] { "Link Purpose (In Context)", "A", "Operable" };
            dWcag["2.4.5"] = new string[] { "Multiple Ways", "AA", "Operable" };
            dWcag["2.4.6"] = new string[] { "Headings and Labels", "AA", "Operable" };
            dWcag["2.4.7"] = new string[] { "Focus Visible", "AA", "Operable" };
            dWcag["2.4.8"] = new string[] { "Location", "AAA", "Operable" };
            dWcag["2.4.9"] = new string[] { "Link Purpose (Link Only)", "AAA", "Operable" };
            dWcag["2.4.10"] = new string[] { "Section Headings", "AAA", "Operable" };
            dWcag["2.4.11"] = new string[] { "Focus Not Obscured (Minimum)", "AA", "Operable" };
            dWcag["2.4.12"] = new string[] { "Focus Not Obscured (Enhanced)", "AAA", "Operable" };
            dWcag["2.4.13"] = new string[] { "Focus Appearance", "AA", "Operable" };
            dWcag["2.5.1"] = new string[] { "Pointer Gestures", "A", "Operable" };
            dWcag["2.5.2"] = new string[] { "Pointer Cancellation", "A", "Operable" };
            dWcag["2.5.3"] = new string[] { "Label in Name", "A", "Operable" };
            dWcag["2.5.4"] = new string[] { "Motion Actuation", "A", "Operable" };
            dWcag["2.5.5"] = new string[] { "Target Size (Enhanced)", "AAA", "Operable" };
            dWcag["2.5.6"] = new string[] { "Concurrent Input Mechanisms", "AAA", "Operable" };
            dWcag["2.5.7"] = new string[] { "Dragging Movements", "AA", "Operable" };
            dWcag["2.5.8"] = new string[] { "Target Size (Minimum)", "AA", "Operable" };
            dWcag["3.1.1"] = new string[] { "Language of Page", "A", "Understandable" };
            dWcag["3.1.2"] = new string[] { "Language of Parts", "AA", "Understandable" };
            dWcag["3.1.3"] = new string[] { "Unusual Words", "AAA", "Understandable" };
            dWcag["3.1.4"] = new string[] { "Abbreviations", "AAA", "Understandable" };
            dWcag["3.1.5"] = new string[] { "Reading Level", "AAA", "Understandable" };
            dWcag["3.1.6"] = new string[] { "Pronunciation", "AAA", "Understandable" };
            dWcag["3.2.1"] = new string[] { "On Focus", "A", "Understandable" };
            dWcag["3.2.2"] = new string[] { "On Input", "A", "Understandable" };
            dWcag["3.2.3"] = new string[] { "Consistent Navigation", "AA", "Understandable" };
            dWcag["3.2.4"] = new string[] { "Consistent Identification", "AA", "Understandable" };
            dWcag["3.2.5"] = new string[] { "Change on Request", "AAA", "Understandable" };
            dWcag["3.2.6"] = new string[] { "Consistent Help", "A", "Understandable" };
            dWcag["3.3.1"] = new string[] { "Error Identification", "A", "Understandable" };
            dWcag["3.3.2"] = new string[] { "Labels or Instructions", "A", "Understandable" };
            dWcag["3.3.3"] = new string[] { "Error Suggestion", "AA", "Understandable" };
            dWcag["3.3.4"] = new string[] { "Error Prevention (Legal, Financial, Data)", "AA", "Understandable" };
            dWcag["3.3.5"] = new string[] { "Help", "AAA", "Understandable" };
            dWcag["3.3.6"] = new string[] { "Error Prevention (All)", "AAA", "Understandable" };
            dWcag["3.3.7"] = new string[] { "Redundant Entry", "A", "Understandable" };
            dWcag["3.3.8"] = new string[] { "Accessible Authentication (Minimum)", "AA", "Understandable" };
            dWcag["3.3.9"] = new string[] { "Accessible Authentication (Enhanced)", "AAA", "Understandable" };
            dWcag["4.1.1"] = new string[] { "Parsing", "A", "Robust" };
            dWcag["4.1.2"] = new string[] { "Name, Role, Value", "A", "Robust" };
            dWcag["4.1.3"] = new string[] { "Status Messages", "AA", "Robust" };
            return dWcag;
        }

        private static string WcagFromTag(string sTag)
        {
            // axe writes 1.1.1 as wcag111 and 1.4.10 as wcag1410. The first two
            // digits are always one each; whatever follows is the third part.
            Match match = Regex.Match(sTag, "^wcag(\\d)(\\d)(\\d+)$");
            if (!match.Success) return "";
            return match.Groups[1].Value + "." + match.Groups[2].Value + "."
                + match.Groups[3].Value;
        }

        /// <summary>
        /// Runs axe and writes ONE readable file, opened when it is done.
        ///
        /// His rule for this one: a single file, so no folder — Downloads
        /// holding "Axe-&lt;page title&gt;.htm". The shape follows report.py, which
        /// took it from urlCheck: a plain-language summary first, then the
        /// severity breakdown, then each violation with its WCAG criterion
        /// NAMED and its level given, the places it occurs, and the engine's
        /// own explanation of why.
        ///
        /// One thing from urlCheck is deliberately left out, as report.py also
        /// leaves it out: a coloured emoji beside each severity. A screen
        /// reader says "red circle" immediately before the word "critical", so
        /// the severity arrives twice and one of them is noise.
        /// </summary>
        private static string AxeReport()
        {
            if (!InjectEngine(sAxeCacheName, lAxeUrls, sAxePresent, 200000))
                return "{\"error\":\"The axe engine could not be loaded. Check the internet connection.\"}";

            string sTitle = Tidy(EvaluateText("(() => document.title)()"));
            string sUrl = Tidy(EvaluateText("(() => location.href)()"));
            if (sTitle == "" || sTitle.StartsWith("ERROR:")) sTitle = sUrl;

            string sJson = EvaluateText(
                "(async () => { const d = await axe.run(document, {"
                + " runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','best-practice']},"
                + " resultTypes: ['violations','incomplete','passes','inapplicable']});"
                + " return JSON.stringify({violations: d.violations, incomplete: d.incomplete,"
                + " passes: d.passes.length, inapplicable: d.inapplicable.length}); })()");
            if (sJson == null || sJson == "" || sJson.StartsWith("ERROR:"))
                return "{\"error\":\"The axe engine returned no results.\"}";

            string sXml = JsonToXml(sJson);
            if (sXml == null)
                return "{\"error\":\"The axe results could not be read.\"}";
            var oDocument = new XmlDocument();
            try { oDocument.LoadXml(sXml); }
            catch { return "{\"error\":\"The axe results could not be read.\"}"; }

            var dWcag = WcagTable();
            var oBody = new StringBuilder();
            var lTopRules = new List<string>();
            var lRuleCounts = new List<KeyValuePair<int, string>>();
            int iViolations = 0;
            int iPlaces = 0;
            int iWeighted = 0;
            int iPageBytes = 0;
            int.TryParse(EvaluateText(
                "(() => String(document.documentElement.outerHTML.length))()"),
                out iPageBytes);
            var dImpact = new Dictionary<string, int>();
            foreach (string sName in new string[] { "critical", "serious", "moderate", "minor" })
                dImpact[sName] = 0;

            foreach (string sGroup in new string[] { "violations", "incomplete" })
            {
                XmlNodeList lItems = oDocument.SelectNodes("/root/" + sGroup + "/item");
                if (lItems.Count == 0) continue;
                oBody.Append("<h2 id=\"" + sGroup + "\">"
                    + (sGroup == "violations" ? "Problems" : "Worth reviewing by hand")
                    + " (" + lItems.Count.ToString() + ")</h2>\r\n");
                foreach (XmlNode oItem in lItems)
                {
                    XmlNode oImpact = oItem.SelectSingleNode("impact");
                    XmlNode oHelp = oItem.SelectSingleNode("help");
                    XmlNode oId = oItem.SelectSingleNode("id");
                    XmlNode oDescription = oItem.SelectSingleNode("description");
                    XmlNode oHelpUrl = oItem.SelectSingleNode("helpUrl");
                    XmlNodeList lNodes = oItem.SelectNodes("nodes/item");
                    string sImpact = oImpact == null ? "" : oImpact.InnerText;
                    if (sGroup == "violations")
                    {
                        iViolations += 1;
                        iPlaces += lNodes.Count;
                        if (dImpact.ContainsKey(sImpact)) dImpact[sImpact] = dImpact[sImpact] + 1;
                        // urlCheck's weighting: minor 1, moderate 2,
                        // serious 3, critical 4. Best practice and unknown
                        // impact are left out, having no defined severity.
                        int iWeight = 0;
                        if (sImpact == "minor") iWeight = 1;
                        if (sImpact == "moderate") iWeight = 2;
                        if (sImpact == "serious") iWeight = 3;
                        if (sImpact == "critical") iWeight = 4;
                        iWeighted += iWeight * lNodes.Count;
                        lRuleCounts.Add(new KeyValuePair<int, string>(lNodes.Count,
                            EscapeHtml((oId == null ? "" : oId.InnerText) + " - "
                                + (oHelp == null ? "" : oHelp.InnerText))
                                + ": " + lNodes.Count.ToString()
                                + (lNodes.Count == 1 ? " place" : " places")));
                    }
                    oBody.Append("<h3>" + EscapeHtml(oHelp == null ? "" : oHelp.InnerText)
                        + "</h3>\r\n<ul>\r\n");
                    if (sImpact != "")
                        oBody.Append("<li>Impact: " + EscapeHtml(sImpact) + "</li>\r\n");
                    oBody.Append("<li>Places: " + lNodes.Count.ToString() + "</li>\r\n");
                    var lCriteria = new List<string>();
                    foreach (XmlNode oTag in oItem.SelectNodes("tags/item"))
                    {
                        string sNumber = WcagFromTag(oTag.InnerText);
                        if (sNumber == "" || !dWcag.ContainsKey(sNumber)) continue;
                        string[] lFacts = dWcag[sNumber];
                        lCriteria.Add(sNumber + " " + lFacts[0] + ", Level " + lFacts[1]
                            + ", " + lFacts[2]);
                    }
                    if (lCriteria.Count > 0)
                        oBody.Append("<li>WCAG: " + EscapeHtml(
                            string.Join("; ", lCriteria.ToArray())) + "</li>\r\n");
                    else
                        oBody.Append("<li>Best practice, not a WCAG requirement</li>\r\n");
                    if (oDescription != null)
                        oBody.Append("<li>" + EscapeHtml(oDescription.InnerText) + "</li>\r\n");
                    if (oId != null)
                        oBody.Append("<li>Rule: " + EscapeHtml(oId.InnerText) + "</li>\r\n");
                    if (oHelpUrl != null)
                        oBody.Append("<li><a href=\"" + EscapeHtml(oHelpUrl.InnerText)
                            + "\">How to fix it</a></li>\r\n");
                    oBody.Append("</ul>\r\n");
                    int iShown = 0;
                    foreach (XmlNode oNode in lNodes)
                    {
                        if (iShown >= 5) break;
                        iShown += 1;
                        XmlNode oTarget = oNode.SelectSingleNode("target/item");
                        XmlNode oHtml = oNode.SelectSingleNode("html");
                        XmlNode oSummary = oNode.SelectSingleNode("failureSummary");
                        oBody.Append("<h4>Place " + iShown.ToString() + "</h4>\r\n<ul>\r\n");
                        if (oTarget != null)
                            oBody.Append("<li>Selector: <code>"
                                + EscapeHtml(oTarget.InnerText) + "</code></li>\r\n");
                        if (oHtml != null)
                        {
                            string sSnippet = Tidy(oHtml.InnerText);
                            if (sSnippet.Length > 300) sSnippet = sSnippet.Substring(0, 300);
                            oBody.Append("<li>Element: <code>" + EscapeHtml(sSnippet)
                                + "</code></li>\r\n");
                        }
                        if (oSummary != null)
                            oBody.Append("<li>" + EscapeHtml(Tidy(oSummary.InnerText))
                                + "</li>\r\n");
                        oBody.Append("</ul>\r\n");
                    }
                    if (lNodes.Count > iShown)
                        oBody.Append("<p>And " + (lNodes.Count - iShown).ToString()
                            + " more places.</p>\r\n");
                }
            }

            lRuleCounts.Sort(delegate (KeyValuePair<int, string> a,
                KeyValuePair<int, string> b) { return b.Key.CompareTo(a.Key); });
            for (int i = 0; i < lRuleCounts.Count && i < 3; i++)
                lTopRules.Add(lRuleCounts[i].Value);

            XmlNode oPasses = oDocument.SelectSingleNode("/root/passes");
            XmlNode oInapplicable = oDocument.SelectSingleNode("/root/inapplicable");
            var oText = new StringBuilder();
            oText.Append("<!DOCTYPE html>\r\n<html lang=\"en\">\r\n<head>\r\n");
            oText.Append("<meta charset=\"utf-8\">\r\n<title>Accessibility report: ");
            oText.Append(EscapeHtml(sTitle));
            oText.Append("</title>\r\n</head>\r\n<body>\r\n<h1>Accessibility report</h1>\r\n");
            oText.Append("<p><a href=\"#violations\">Skip to the problems</a></p>\r\n");
            oText.Append("<h2>In plain words</h2>\r\n<p>");
            if (iViolations == 0)
                oText.Append("Nothing failed automatically. That is not the same as "
                    + "being accessible: an automated engine finds perhaps a third of "
                    + "what a person would.");
            else
                oText.Append("This page has " + iViolations.ToString()
                    + " kinds of confirmed problem in " + iPlaces.ToString()
                    + " places. An automated engine finds perhaps a third of what a "
                    + "person testing by hand would, so this is a floor rather than a "
                    + "verdict.");
            oText.Append("</p>\r\n<h2>What was tested</h2>\r\n<ul>\r\n");
            oText.Append("<li>Page: " + EscapeHtml(sTitle) + "</li>\r\n");
            oText.Append("<li>Address: <a href=\"" + EscapeHtml(sUrl) + "\">"
                + EscapeHtml(sUrl) + "</a></li>\r\n");
            oText.Append("<li>Engine: Deque axe-core</li>\r\n");
            oText.Append("<li>Standards: WCAG 2.0 A and AA, WCAG 2.1 AA, and best practice</li>\r\n");
            oText.Append("<li>Tested: " + DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "</li>\r\n");
            oText.Append("</ul>\r\n<h2>How much was found</h2>\r\n<ul>\r\n");
            foreach (string sName in new string[] { "critical", "serious", "moderate", "minor" })
                oText.Append("<li>" + dImpact[sName].ToString() + " " + sName + "</li>\r\n");
            if (oPasses != null)
                oText.Append("<li>" + EscapeHtml(oPasses.InnerText) + " kinds of check passed</li>\r\n");
            if (oInapplicable != null)
                oText.Append("<li>" + EscapeHtml(oInapplicable.InnerText)
                    + " kinds of check did not apply to this page</li>\r\n");
            // THE FAILURE RATE, from urlCheck. One comparable number where
            // the counts alone are not: four criticals and four minors both
            // report "4". Weighted faults over the size of the page, so a
            // long page with a few faults does not look worse than a short
            // one riddled with them.
            if (iPageBytes > 0)
            {
                double nRate = 1000.0 * (double) iWeighted / (double) iPageBytes;
                oText.Append("<li>Failure rate: " + nRate.ToString("0.0")
                    + " weighted faults per thousand bytes of page. Lower is "
                    + "better, and it is for comparing this page with itself "
                    + "over time rather than with another site.</li>\r\n");
            }
            oText.Append("</ul>\r\n");
            if (lTopRules.Count > 0)
            {
                oText.Append("<h2>The most common problems</h2>\r\n<ul>\r\n");
                foreach (string sTop in lTopRules)
                    oText.Append("<li>" + sTop + "</li>\r\n");
                oText.Append("</ul>\r\n");
            }
            if (iViolations > 0)
            {
                oText.Append("<h2>Recommended next steps</h2>\r\n<ol>\r\n");
                oText.Append("<li>Start with the critical and serious problems. They have the most effect on people using assistive technology.</li>\r\n");
                oText.Append("<li>Use the selector and element shown with each place to find the exact thing in your code.</li>\r\n");
                oText.Append("<li>Follow the how-to-fix link for each rule, then run this again to confirm the fix.</li>\r\n");
                oText.Append("<li>After the automatic problems are fixed, test by hand with a screen reader and with the keyboard alone.</li>\r\n");
                oText.Append("<li>An automated tool finds roughly thirty to forty per cent of accessibility problems. Manual testing and feedback from people who use assistive technology are needed for the rest.</li>\r\n");
                oText.Append("</ol>\r\n");
            }
            oText.Append(oBody.ToString());
            oText.Append("</body>\r\n</html>\r\n");

            // One file, so no folder: Downloads, named for the page.
            string sName2 = "Axe-" + SafeStem(sTitle) + ".htm";
            string sPath = Path.Combine(DownloadsFolder(), sName2);
            try
            {
                File.WriteAllText(sPath, oText.ToString(), new UTF8Encoding(true));
            }
            catch (Exception oError)
            {
                return "{\"error\":" + Quote("The report could not be saved: "
                    + oError.Message) + "}";
            }
            Log("  wrote " + sPath + ", " + new FileInfo(sPath).Length.ToString() + " bytes");
            string sOpened = OpenInTab(new Uri(sPath).AbsoluteUri);
            return "{\"value\":" + Quote(iViolations.ToString()
                + " kinds of problem in " + iPlaces.ToString() + " places. Saved as "
                + sName2 + " in Downloads. The report is " + sOpened) + "}";
        }

        // --- File dialogs and converters -------------------------------------

        /// <summary>
        /// THE OLD WINDOWS FILE DIALOG, ON PURPOSE.
        ///
        /// .NET's OpenFileDialog and SaveFileDialog show the Vista-era Common
        /// Item Dialog by default. AutoUpgradeEnabled = false brings back the
        /// classic GetOpenFileName one, which is what a screen reader user
        /// actually wants here: a plain list, a real folder tree, and Tab
        /// order that goes where you expect. The modern dialog is prettier and
        /// harder to navigate without sight, and this is his call, not mine.
        ///
        /// Marked STAThread already, which the dialogs require.
        /// </summary>
        private static string FileDialog(string sArgument, bool bSave)
        {
            // Argument is title, then filter, then the path to start at, tab
            // separated. Any of them may be empty.
            string[] lParts = (sArgument ?? "").Split('\t');
            string sTitle = lParts.Length > 0 ? lParts[0] : "";
            string sFilter = lParts.Length > 1 ? lParts[1] : "";
            string sStart = lParts.Length > 2 ? lParts[2] : "";
            if (sTitle == "") sTitle = bSave ? "Save as" : "Open";
            if (sFilter == "") sFilter = "All files|*.*";

            try
            {
                using (var oDialog = bSave
                    ? (System.Windows.Forms.FileDialog) new System.Windows.Forms.SaveFileDialog()
                    : (System.Windows.Forms.FileDialog) new System.Windows.Forms.OpenFileDialog())
                {
                    oDialog.AutoUpgradeEnabled = false;
                    oDialog.Title = sTitle;
                    oDialog.Filter = sFilter;
                    oDialog.RestoreDirectory = true;
                    if (sStart != "")
                    {
                        try
                        {
                            string sFolder = Path.GetDirectoryName(sStart);
                            if (!string.IsNullOrEmpty(sFolder) && Directory.Exists(sFolder))
                                oDialog.InitialDirectory = sFolder;
                            oDialog.FileName = Path.GetFileName(sStart);
                        }
                        catch (Exception) { }
                    }
                    var oSave = oDialog as System.Windows.Forms.SaveFileDialog;
                    if (oSave != null) oSave.OverwritePrompt = true;
                    // Brought to the front, because a dialog opened by a
                    // program the user did not start can otherwise appear
                    // behind the browser and be announced by nothing.
                    if (oDialog.ShowDialog() != System.Windows.Forms.DialogResult.OK)
                        return "{\"error\":\"Cancelled.\"}";
                    Log("  the dialog chose " + oDialog.FileName);
                    return "{\"value\":" + Quote(oDialog.FileName) + "}";
                }
            }
            catch (Exception oError)
            {
                return "{\"error\":" + Quote(oError.Message) + "}";
            }
        }

        /// <summary>
        /// Where a converter lives, following the NVDA side's own search.
        ///
        /// CONVERTERS ARE FOUND, NOT BUNDLED. A program folder is replaced
        /// wholesale on update, and some managed environments will not execute
        /// from a roaming profile. So HomerView looks where these things
        /// already are and says plainly when one is absent.
        /// </summary>
        private static string FindConverter(string sName)
        {
            var lCandidates = new List<string>();
            string sHere = Path.GetDirectoryName(
                System.Reflection.Assembly.GetExecutingAssembly().Location);
            lCandidates.Add(Path.Combine(sHere, sName));
            foreach (string sVariable in new string[] {
                "PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA" })
            {
                string sRoot = Environment.GetEnvironmentVariable(sVariable);
                if (string.IsNullOrEmpty(sRoot)) continue;
                foreach (string sFolder in new string[] {
                    "HomerView", "Homer", "Pandoc", "2htm" })
                    lCandidates.Add(Path.Combine(Path.Combine(sRoot, sFolder), sName));
            }
            lCandidates.Add(Path.Combine("C:\\HomerView", sName));
            lCandidates.Add(Path.Combine("C:\\2htm", sName));
            foreach (string sFolder in
                (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
            {
                if (sFolder.Trim() == "") continue;
                try { lCandidates.Add(Path.Combine(sFolder.Trim(), sName)); }
                catch (Exception) { }
            }
            foreach (string sCandidate in lCandidates)
            {
                try
                {
                    if (File.Exists(sCandidate))
                    {
                        Log("  " + sName + " found at " + sCandidate);
                        return sCandidate;
                    }
                }
                catch (Exception) { }
            }
            Log("  " + sName + " was not found anywhere");
            return "";
        }

        private static int RunAndWait(string sProgram, string sArguments)
        {
            var oStart = new ProcessStartInfo(sProgram, sArguments);
            oStart.UseShellExecute = false;
            oStart.CreateNoWindow = true;
            oStart.RedirectStandardOutput = true;
            oStart.RedirectStandardError = true;
            using (var oProcess = Process.Start(oStart))
            {
                string sOut = oProcess.StandardOutput.ReadToEnd();
                string sErr = oProcess.StandardError.ReadToEnd();
                oProcess.WaitForExit(120000);
                if (sOut.Trim() != "") Log("    " + Abbreviate(sOut.Trim(), 300));
                if (sErr.Trim() != "") Log("    " + Abbreviate(sErr.Trim(), 300));
                return oProcess.ExitCode;
            }
        }

        // Which converter handles which format, in the order the NVDA side
        // prefers. Anything not listed the browser opens by itself.
        private static string[] ConvertersFor(string sExtension)
        {
            switch (sExtension)
            {
                case ".docx": case ".odt": case ".rtf": case ".md":
                case ".markdown": case ".epub": case ".txt2":
                    return new string[] { "pandoc.exe", "2htm.exe" };
                case ".pdf": case ".doc": case ".ppt": case ".pptx":
                case ".xls": case ".xlsx": case ".csv":
                    return new string[] { "2htm.exe" };
                default:
                    return new string[] { };
            }
        }

        /// <summary>
        /// Turns a document into a temporary web page, and says where it is.
        ///
        /// The browser opens html, text, images and pdf-in-a-viewer on its own;
        /// everything else needs a converter first. The result goes in
        /// HomerView's temp folder rather than beside the original, because the
        /// original may be somewhere the user cannot write and because a
        /// converted copy is not a document anybody meant to keep.
        /// </summary>
        private static string ToWebPage(string sPath)
        {
            if (string.IsNullOrEmpty(sPath) || !File.Exists(sPath))
                return "{\"error\":" + Quote("There is no file at " + sPath) + "}";
            string sExtension = Path.GetExtension(sPath).ToLowerInvariant();
            if (sExtension == ".htm" || sExtension == ".html" || sExtension == ".txt"
                || sExtension == ".xml" || sExtension == ".svg")
                return "{\"value\":" + Quote(sPath) + "}";

            string[] lConverters = ConvertersFor(sExtension);
            if (lConverters.Length == 0)
                return "{\"value\":" + Quote(sPath) + "}";

            string sFolder = Path.Combine(
                Directory.GetParent(ProfileFolder()).FullName, "temp");
            Directory.CreateDirectory(sFolder);
            string sTarget = Path.Combine(sFolder,
                SafeStem(Path.GetFileNameWithoutExtension(sPath)) + ".htm");
            try { if (File.Exists(sTarget)) File.Delete(sTarget); }
            catch (Exception) { }

            var lTried = new List<string>();
            foreach (string sConverter in lConverters)
            {
                string sProgram = FindConverter(sConverter);
                if (sProgram == "") { lTried.Add(sConverter + " is not installed"); continue; }
                try
                {
                    string sArguments = sConverter == "pandoc.exe"
                        ? "\"" + sPath + "\" -s -o \"" + sTarget + "\""
                        : "\"" + sPath + "\" \"" + sTarget + "\"";
                    Log("  converting with " + sProgram);
                    int iExit = RunAndWait(sProgram, sArguments);
                    if (File.Exists(sTarget) && new FileInfo(sTarget).Length > 0)
                    {
                        Log("  wrote " + sTarget + ", "
                            + new FileInfo(sTarget).Length.ToString() + " bytes");
                        return "{\"value\":" + Quote(sTarget) + "}";
                    }
                    lTried.Add(sConverter + " ended with code " + iExit.ToString()
                        + " and wrote nothing");
                }
                catch (Exception oError)
                {
                    lTried.Add(sConverter + " failed: " + oError.Message);
                }
            }
            return "{\"error\":" + Quote("This " + sExtension.TrimStart('.')
                + " file could not be converted. " + string.Join("; ", lTried.ToArray())
                + ". Converters are found rather than bundled, so installing pandoc "
                + "or 2htm makes this work.") + "}";
        }

        /// <summary>
        /// Opens a document: convert if it needs it, then a HomerView tab.
        /// </summary>
        private static string OpenDocument(string sPath)
        {
            string sConverted = ToWebPage(sPath);
            if (sConverted.StartsWith("{\"error\""))
                return sConverted;
            string sPage = XmlTextFromJson(sConverted);
            if (sPage == "")
                return "{\"error\":\"Nothing came back from the conversion.\"}";
            return OpenPage(sPage);
        }

        // The envelope is built here, so reading a value back out of it should
        // not need the browser or the scripts.
        private static string XmlTextFromJson(string sJson)
        {
            Match match = Regex.Match(sJson, "\"value\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
            return match.Success ? Unescape(match.Groups[1].Value) : "";
        }

        /// <summary>
        /// Saves the page the reader is on, converting when the chosen name
        /// asks for something other than a web page.
        /// </summary>
        private static string SavePage(string sPath)
        {
            if (string.IsNullOrEmpty(sPath))
                return "{\"error\":\"No file was named.\"}";
            string sHtml = EvaluateText(
                "(() => document.documentElement.outerHTML)()");
            if (sHtml == null || sHtml == "" || sHtml.StartsWith("ERROR:"))
                return "{\"error\":\"The page's own source could not be read.\"}";
            string sExtension = Path.GetExtension(sPath).ToLowerInvariant();
            try
            {
                string sFolder = Path.GetDirectoryName(sPath);
                if (!string.IsNullOrEmpty(sFolder)) Directory.CreateDirectory(sFolder);
                if (sExtension == ".htm" || sExtension == ".html")
                {
                    File.WriteAllText(sPath, sHtml, new UTF8Encoding(true));
                    return "{\"value\":" + Quote("Saved " + sPath + ", "
                        + new FileInfo(sPath).Length.ToString() + " bytes.") + "}";
                }
                // Anything else goes through pandoc, from a temporary copy of
                // the page rather than from the address, so what is saved is
                // the page as read rather than as fetched again.
                string sPandoc = FindConverter("pandoc.exe");
                if (sPandoc == "")
                    return "{\"error\":\"Saving in that format needs pandoc, which is not installed. A .htm name always works.\"}";
                string sTemp = Path.Combine(
                    Path.Combine(Directory.GetParent(ProfileFolder()).FullName, "temp"),
                    "SavePage.htm");
                Directory.CreateDirectory(Path.GetDirectoryName(sTemp));
                File.WriteAllText(sTemp, sHtml, new UTF8Encoding(true));
                int iExit = RunAndWait(sPandoc,
                    "\"" + sTemp + "\" -s -o \"" + sPath + "\"");
                if (File.Exists(sPath) && new FileInfo(sPath).Length > 0)
                    return "{\"value\":" + Quote("Saved " + sPath + ", "
                        + new FileInfo(sPath).Length.ToString() + " bytes.") + "}";
                return "{\"error\":" + Quote("pandoc ended with code "
                    + iExit.ToString() + " and wrote nothing.") + "}";
            }
            catch (Exception oError)
            {
                return "{\"error\":" + Quote(oError.Message) + "}";
            }
        }

        // --- Web download ----------------------------------------------------

        /// <summary>
        /// WHERE CDP ENDS AND .NET BEGINS, and why the line is drawn there.
        ///
        /// The browser is not asked to download anything. It is asked what it
        /// KNOWS, and .NET makes the request with what it said.
        ///
        /// CDP supplies four things nothing else can: the links on the page
        /// after script has run, the session's COOKIES for that address, the
        /// browser's own USER AGENT, and the address of the page the link sits
        /// on. .NET then issues the request carrying all of it, plus the
        /// Sec-Fetch headers a click would have produced.
        ///
        /// The alternative was letting Edge download through
        /// Browser.setDownloadBehavior. It was rejected: the browser picks the
        /// name, reports failure as a shelf entry rather than an error, offers
        /// no progress a script can read, and its own download prompts can
        /// intervene. Fetching directly gives the Content-Disposition name, the
        /// real HTTP status when something refuses, and a file on disk when the
        /// call returns.
        ///
        /// The headers are the whole trick. Sites gate files on the Referer,
        /// and many inspect Sec-Fetch. A request without them looks like a
        /// scraper and comes back 403 or as a login page rather than the file.
        /// </summary>
        private const string sLinkScript = @"(() => {
    const dMime = {
        ""application/pdf"": ""pdf"", ""application/zip"": ""zip"",
        ""application/epub+zip"": ""epub"", ""application/rtf"": ""rtf"",
        ""application/msword"": ""doc"", ""application/vnd.ms-excel"": ""xls"",
        ""application/vnd.ms-powerpoint"": ""ppt"", ""application/json"": ""json"",
        ""application/vnd.openxmlformats-officedocument.wordprocessingml.document"": ""docx"",
        ""application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"": ""xlsx"",
        ""application/vnd.openxmlformats-officedocument.presentationml.presentation"": ""pptx"",
        ""text/csv"": ""csv"", ""text/plain"": ""txt"", ""text/html"": ""html"",
        ""image/jpeg"": ""jpg"", ""image/png"": ""png"", ""image/gif"": ""gif"",
        ""image/svg+xml"": ""svg"", ""audio/mpeg"": ""mp3"", ""video/mp4"": ""mp4""
    };
    const extensionOf = (sName) => {
        if (!sName) return """";
        const sClean = sName.split(""?"")[0].split(""#"")[0];
        const iDot = sClean.lastIndexOf(""."");
        const iSlash = sClean.lastIndexOf(""/"");
        if (iDot <= iSlash + 1) return """";
        const sExtension = sClean.slice(iDot + 1).toLowerCase();
        return /^[a-z0-9]{1,8}$/.test(sExtension) ? sExtension : """";
    };
    const lOut = [];
    const setSeen = new Set();
    for (const el of Array.from(document.querySelectorAll(
            ""a[href], area[href], link[href][download]""))) {
        let sAbsolute = """";
        try { sAbsolute = new URL(el.getAttribute(""href""), window.location.href).href; }
        catch (error) { continue; }
        if (!sAbsolute.startsWith(""http"")) continue;
        if (setSeen.has(sAbsolute)) continue;
        let sExtension = """";
        const sDownload = el.getAttribute(""download"");
        if (sDownload) sExtension = extensionOf(sDownload);
        if (!sExtension) {
            try { sExtension = extensionOf(new URL(sAbsolute).pathname); }
            catch (error) { sExtension = """"; }
        }
        if (!sExtension) {
            const sType = (el.getAttribute(""type"") || """").toLowerCase().split("";"")[0].trim();
            if (dMime[sType]) sExtension = dMime[sType];
        }
        if (!sExtension && el.hasAttribute(""download"")) sExtension = ""unknown"";
        if (!sExtension) continue;
        setSeen.add(sAbsolute);
        lOut.push(sExtension + ""\t"" + sAbsolute + ""\t""
            + (el.textContent || el.getAttribute(""aria-label"") || """").trim().slice(0, 120));
    }
    return lOut.join(""\n"");
})()";

        // Server-side page addresses, never a file worth fetching.
        private static readonly string[] lSkipExtensions = new string[] {
            "asp", "aspx", "cfm", "cgi", "do", "jsp", "php", "pl", "py" };
        // Listed and available by typing, but not filled in for you: page
        // addresses and script assets are numerous and rarely wanted.
        private static readonly string[] lNotByDefault = new string[] {
            "css", "htm", "html", "js", "json", "shtml", "xhtml", "xml" };

        private static string ExtensionName(string sExtension)
        {
            switch (sExtension)
            {
                case "7z": return "7-Zip archive";
                case "csv": return "Comma separated values";
                case "doc": case "docx": return "Word document";
                case "epub": return "EPUB ebook";
                case "exe": return "Windows program";
                case "gif": return "GIF image";
                case "gz": case "tar": case "zip": case "rar": return "Archive";
                case "htm": case "html": return "Web page";
                case "jpg": case "jpeg": return "JPEG image";
                case "json": return "JSON data";
                case "m4a": case "aac": case "flac": case "ogg": case "wav":
                    return "Audio";
                case "m4b": return "M4B audiobook";
                case "md": return "Markdown";
                case "mobi": return "Mobipocket ebook";
                case "mp3": return "MP3 audio";
                case "mp4": case "avi": return "Video";
                case "msi": return "Windows installer";
                case "odp": return "OpenDocument presentation";
                case "ods": return "OpenDocument spreadsheet";
                case "odt": return "OpenDocument text";
                case "pdf": return "PDF document";
                case "png": case "bmp": return "Image";
                case "ppt": case "pptx": return "PowerPoint presentation";
                case "rtf": return "Rich text";
                case "svg": return "SVG image";
                case "txt": return "Plain text";
                case "xls": case "xlsx": return "Excel spreadsheet";
                case "unknown": return "Named by the server";
                default: return "";
            }
        }

        private static bool InList(string[] lList, string sValue)
        {
            foreach (string s in lList) if (s == sValue) return true;
            return false;
        }

        private static List<string[]> DownloadLinks()
        {
            var lLinks = new List<string[]>();
            string sFound = EvaluateText(sLinkScript);
            if (sFound == null || sFound == "" || sFound.StartsWith("ERROR:"))
                return lLinks;
            foreach (string sLine in sFound.Split('\n'))
            {
                string[] lParts = sLine.Split('\t');
                if (lParts.Length < 2) continue;
                if (InList(lSkipExtensions, lParts[0])) continue;
                lLinks.Add(new string[] { lParts[0], lParts[1],
                    lParts.Length > 2 ? lParts[2] : "" });
            }
            return lLinks;
        }

        /// <summary>
        /// What is on the page and what would be fetched by default.
        /// </summary>
        private static string DownloadScan()
        {
            var lLinks = DownloadLinks();
            if (lLinks.Count == 0)
                return "{\"error\":\"No files are linked from this page.\"}";
            var dCounts = new Dictionary<string, int>();
            foreach (string[] lLink in lLinks)
            {
                if (!dCounts.ContainsKey(lLink[0])) dCounts[lLink[0]] = 0;
                dCounts[lLink[0]] = dCounts[lLink[0]] + 1;
            }
            var lKinds = new List<string>(dCounts.Keys);
            lKinds.Sort();
            var oSummary = new StringBuilder();
            var lDefault = new List<string>();
            foreach (string sKind in lKinds)
            {
                string sWhat = ExtensionName(sKind);
                oSummary.Append(sKind + ": "
                    + (sWhat == "" ? "" : sWhat + ", ")
                    + dCounts[sKind].ToString() + ". ");
                if (!InList(lNotByDefault, sKind)) lDefault.Add(sKind);
            }
            // Summary first, then a tab, then what to fill in for the reader.
            return "{\"value\":" + Quote(oSummary.ToString().Trim()
                + "\t" + string.Join(" ", lDefault.ToArray())) + "}";
        }

        /// <summary>The cookies the browser would send, as a header.</summary>
        private static string CookieHeader(string sUrl)
        {
            try
            {
                string sSocket = FindActivePageSocket();
                if (sSocket == null) return "";
                string sAnswer = SendAndWait(sSocket,
                    "{\"id\":1,\"method\":\"Network.getCookies\",\"params\":{\"urls\":["
                    + Quote(sUrl) + "]}}");
                if (sAnswer == null || !sAnswer.Contains("\"cookies\""))
                {
                    // The domain has to be enabled before it will answer on
                    // some pages. Asking twice is cheaper than never asking.
                    SendAndWait(sSocket, "{\"id\":2,\"method\":\"Network.enable\"}");
                    sAnswer = SendAndWait(sSocket,
                        "{\"id\":3,\"method\":\"Network.getCookies\",\"params\":{\"urls\":["
                        + Quote(sUrl) + "]}}");
                }
                if (sAnswer == null) return "";
                var lPairs = new List<string>();
                foreach (Match match in Regex.Matches(sAnswer,
                    "\\{[^{}]*?\"name\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"[^{}]*?\"value\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"[^{}]*?\\}"))
                {
                    lPairs.Add(Unescape(match.Groups[1].Value) + "="
                        + Unescape(match.Groups[2].Value));
                }
                Log("  the browser reports " + lPairs.Count.ToString() + " cookies for that address");
                return string.Join("; ", lPairs.ToArray());
            }
            catch (Exception oError)
            {
                Log("  cookies could not be read: " + oError.Message);
                return "";
            }
        }

        private static string CleanFileName(string sName, string sExtension)
        {
            string sClean = Uri.UnescapeDataString(sName ?? "").Trim().Trim('.');
            sClean = Regex.Replace(sClean, "[<>:\"/\\\\|?*\\x00-\\x1f]", "_");
            sClean = Regex.Replace(sClean, "\\s+", " ").Trim();
            if (sClean == "") sClean = "download";
            if (sClean.Length > 120) sClean = sClean.Substring(0, 120);
            if (sExtension != "" && sExtension != "unknown"
                && !sClean.ToLowerInvariant().EndsWith("." + sExtension))
                sClean = sClean + "." + sExtension;
            return sClean;
        }

        private static string UniqueIn(string sFolder, string sName)
        {
            string sPath = Path.Combine(sFolder, sName);
            if (!File.Exists(sPath)) return sPath;
            string sStem = Path.GetFileNameWithoutExtension(sName);
            string sExtension = Path.GetExtension(sName);
            for (int i = 2; i < 500; i++)
            {
                sPath = Path.Combine(sFolder,
                    sStem + " (" + i.ToString() + ")" + sExtension);
                if (!File.Exists(sPath)) return sPath;
            }
            return sPath;
        }

        /// <summary>
        /// Fetches every link of the kinds asked for, into a folder named after
        /// the page under Downloads.
        ///
        /// The folder is KEPT rather than emptied, unlike the accessibility
        /// results: a download is something a person meant to keep, and a
        /// second run on the same page should add to what is there rather than
        /// throw it away. Names that already exist are numbered as Windows
        /// numbers them.
        /// </summary>
        private static string SessionPath()
        {
            return Path.Combine(Path.GetTempPath(), "HomerViewDownload.txt");
        }

        /// <summary>
        /// Chooses the files and remembers everything needed to fetch them.
        ///
        /// urlFido SPEAKS EACH NAME BEFORE IT FETCHES, and success is the
        /// silence that follows. That cannot be done from one call that fetches
        /// everything, so the work is split: this decides what to fetch and
        /// writes the browser's context beside the list, and DownloadOne
        /// fetches a single file. The context is written once because asking
        /// the browser for cookies and its user agent per file would be
        /// seventeen extra round trips to learn what has not changed.
        /// </summary>
        private static string DownloadList(string sWanted)
        {
            var lWanted = new List<string>();
            foreach (string sPart in Regex.Split(sWanted ?? "", "[\\s,;]+"))
            {
                string sKind = sPart.Trim().TrimStart('.').ToLowerInvariant();
                if (sKind != "") lWanted.Add(sKind);
            }
            if (lWanted.Count == 0)
                return "{\"error\":\"No kinds of file were named, so nothing was fetched.\"}";

            var lChosen = new List<string[]>();
            foreach (string[] lLink in DownloadLinks())
                if (InList(lWanted.ToArray(), lLink[0])) lChosen.Add(lLink);
            if (lChosen.Count == 0)
                return "{\"error\":\"No files of those kinds are linked from this page.\"}";

            string sPageUrl = Tidy(EvaluateText("(() => location.href)()"));
            string sTitle = Tidy(EvaluateText("(() => document.title)()"));
            if (sTitle == "" || sTitle.StartsWith("ERROR:")) sTitle = sPageUrl;
            string sAgent = Tidy(EvaluateText("(() => navigator.userAgent)()"));
            string sCookies = CookieHeader(sPageUrl);
            string sFolder = Path.Combine(DownloadsFolder(), SafeStem(sTitle));
            Directory.CreateDirectory(sFolder);

            var oSession = new StringBuilder();
            oSession.Append(sPageUrl + "\n");
            oSession.Append(sAgent + "\n");
            oSession.Append(sCookies + "\n");
            oSession.Append(sFolder + "\n");
            var oList = new StringBuilder();
            foreach (string[] lLink in lChosen)
            {
                oSession.Append(lLink[0] + "\t" + lLink[1] + "\n");
                // The base name a reader hears before the fetch starts.
                string sName = "";
                try { sName = Path.GetFileName(new Uri(lLink[1]).LocalPath); }
                catch (Exception) { sName = ""; }
                if (sName == "") sName = lLink[2];
                if (sName == "") sName = "a file";
                if (oList.Length > 0) oList.Append("\a");
                oList.Append(Uri.UnescapeDataString(sName));
            }
            File.WriteAllText(SessionPath(), oSession.ToString(), new UTF8Encoding(false));
            Log("  " + lChosen.Count.ToString() + " files to fetch into " + sFolder);
            return "{\"value\":" + Quote(lChosen.Count.ToString() + "\t"
                + sFolder + "\t" + oList.ToString()) + "}";
        }

        /// <summary>Fetches one file from the remembered list, by number.</summary>
        private static string DownloadOne(string sWhich)
        {
            int iWhich = 0;
            int.TryParse((sWhich ?? "").Trim(), out iWhich);
            if (iWhich < 1) return "{\"error\":\"Which file?\"}";
            string[] lSession;
            try { lSession = File.ReadAllText(SessionPath()).Split('\n'); }
            catch (Exception) { return "{\"error\":\"The download list has gone.\"}"; }
            if (lSession.Length < 4 + iWhich)
                return "{\"error\":\"There is no file number " + iWhich.ToString() + ".\"}";
            string sPageUrl = lSession[0];
            string sAgent = lSession[1];
            string sCookies = lSession[2];
            string sFolder = lSession[3];
            string[] lLink = lSession[3 + iWhich].Split('\t');
            if (lLink.Length < 2) return "{\"error\":\"That line of the list is unreadable.\"}";
            return FetchOne(lLink[0], lLink[1], sPageUrl, sAgent, sCookies, sFolder);
        }

        /// <summary>
        /// One file, with the request a click would have made.
        /// </summary>
        private static string FetchOne(string sExtension, string sUrl,
            string sPageUrl, string sAgent, string sCookies, string sFolder)
        {
            try
            {
                ServicePointManager.SecurityProtocol =
                    SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11 | SecurityProtocolType.Tls;
                var oRequest = (HttpWebRequest) WebRequest.Create(sUrl);
                oRequest.Timeout = 25000;
                oRequest.ReadWriteTimeout = 25000;
                oRequest.AllowAutoRedirect = true;
                oRequest.UserAgent = sAgent != "" ? sAgent
                    : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HomerView";
                oRequest.Accept = "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    + "image/avif,image/webp,*/*;q=0.8";
                oRequest.Headers.Add("Accept-Language", "en-US,en;q=0.9");
                oRequest.Headers.Add("Upgrade-Insecure-Requests", "1");
                oRequest.Headers.Add("Sec-Fetch-Dest", "document");
                oRequest.Headers.Add("Sec-Fetch-Mode", "navigate");
                oRequest.Headers.Add("Sec-Fetch-User", "?1");
                if (sCookies != "") oRequest.Headers.Add("Cookie", sCookies);
                if (sPageUrl != "")
                {
                    oRequest.Referer = sPageUrl;
                    try
                    {
                        var oPage = new Uri(sPageUrl);
                        var oFile = new Uri(sUrl);
                        bool bSame = oPage.Host == oFile.Host;
                        oRequest.Headers.Add("Sec-Fetch-Site",
                            bSame ? "same-origin" : "cross-site");
                        if (!bSame)
                            oRequest.Headers.Add("Origin",
                                oPage.Scheme + "://" + oPage.Authority);
                    }
                    catch (Exception) { }
                }
                using (var oResponse = (HttpWebResponse) oRequest.GetResponse())
                {
                    // THE SERVER'S OWN NAME FIRST. Content-Disposition is what
                    // the browser would have saved it as, and on a download
                    // link with no file name in the address it is the only name
                    // there is.
                    string sName = "";
                    string sDisposition = oResponse.Headers["Content-Disposition"];
                    if (!string.IsNullOrEmpty(sDisposition))
                    {
                        Match match = Regex.Match(sDisposition,
                            "filename\\*?=(?:UTF-8'')?\"?([^\";]+)\"?",
                            RegexOptions.IgnoreCase);
                        if (match.Success)
                            sName = Path.GetFileName(match.Groups[1].Value.Trim());
                    }
                    if (sName == "")
                    {
                        try { sName = Path.GetFileName(new Uri(sUrl).LocalPath); }
                        catch (Exception) { sName = ""; }
                    }
                    string sTarget = UniqueIn(sFolder, CleanFileName(sName, sExtension));
                    using (var oIn = oResponse.GetResponseStream())
                    using (var oOut = new FileStream(sTarget, FileMode.Create, FileAccess.Write))
                    {
                        byte[] lBuffer = new byte[65536];
                        int iRead;
                        while ((iRead = oIn.Read(lBuffer, 0, lBuffer.Length)) > 0)
                            oOut.Write(lBuffer, 0, iRead);
                    }
                    long iSize = new FileInfo(sTarget).Length;
                    Log("    " + Path.GetFileName(sTarget) + ", " + iSize.ToString() + " bytes");
                    return "{\"value\":" + Quote(Path.GetFileName(sTarget)
                        + "\t" + iSize.ToString()) + "}";
                }
            }
            catch (WebException oError)
            {
                string sWhy = oError.Message;
                var oBad = oError.Response as HttpWebResponse;
                if (oBad != null)
                    sWhy = ((int) oBad.StatusCode).ToString() + " " + oBad.StatusDescription;
                Log("    FAILED " + sUrl + ": " + sWhy);
                return "{\"error\":" + Quote(sWhy) + "}";
            }
            catch (Exception oError)
            {
                Log("    FAILED " + sUrl + ": " + oError.Message);
                return "{\"error\":" + Quote(oError.Message) + "}";
            }
        }

        // --- Finding, by marking every match ---------------------------------

        /// <summary>
        /// Marks every match in the page and says how many there are.
        ///
        /// THE MARK IS THE WHOLE DESIGN. Searching the virtual buffer from JSL
        /// would mean carrying a position between keystrokes and re-searching
        /// on every Find Again. Instead one pass wraps every match in a span
        /// carrying an attribute of our own, and after that Find Again is just
        /// MoveToTagWithAttribute forwards or backwards -- the same mechanism
        /// Jump to Probable Main already uses, and the same reason: an
        /// attribute is the one thing both the browser and the virtual cursor
        /// can see.
        ///
        /// It also settles "whichever kind of find was used last" for free.
        /// The marks do not remember whether they came from a plain search or
        /// a regular expression, because after marking there is no difference.
        ///
        /// The argument is the mode, a tab, then what to look for. Mode is
        /// "plain" for a case-insensitive substring or "pattern" for a regular
        /// expression.
        /// </summary>
        private static string FindMark(string sArgument)
        {
            string[] lParts = (sArgument ?? "").Split(new char[] { '\t' }, 2);
            if (lParts.Length < 2 || lParts[1] == "")
                return "{\"error\":\"Nothing to look for.\"}";
            bool bPattern = lParts[0] == "pattern";
            string sNeedle = lParts[1];

            // The needle crosses into JavaScript as a string literal, so it is
            // quoted by the same routine that quotes everything else.
            string sScript =
                "(() => {"
                + " for (const el of document.querySelectorAll('[data-homerviewfind]')) {"
                + "   const p = el.parentNode;"
                + "   while (el.firstChild) p.insertBefore(el.firstChild, el);"
                + "   p.removeChild(el); p.normalize();"
                + " }"
                + " let oRe;"
                + " try { oRe = " + (bPattern
                    ? "new RegExp(" + Quote(sNeedle) + ", 'gi')"
                    : "new RegExp(" + Quote(sNeedle)
                      + ".replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'), 'gi')")
                + "; } catch (error) { return 'BAD: ' + error.message; }"
                + " const oWalk = document.createTreeWalker(document.body,"
                + "   NodeFilter.SHOW_TEXT, {"
                + "     acceptNode: (n) => {"
                + "       const sTag = n.parentNode ? n.parentNode.nodeName : '';"
                + "       if (sTag === 'SCRIPT' || sTag === 'STYLE' || sTag === 'NOSCRIPT')"
                + "         return NodeFilter.FILTER_REJECT;"
                + "       return n.nodeValue && n.nodeValue.trim()"
                + "         ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;"
                + "     } });"
                + " const lNodes = [];"
                + " while (oWalk.nextNode()) lNodes.push(oWalk.currentNode);"
                + " let iFound = 0;"
                + " for (const oNode of lNodes) {"
                + "   const sText = oNode.nodeValue;"
                + "   oRe.lastIndex = 0;"
                + "   const lHits = [];"
                + "   let oHit;"
                + "   while ((oHit = oRe.exec(sText)) !== null) {"
                + "     if (oHit[0] === '') { oRe.lastIndex += 1; continue; }"
                + "     lHits.push([oHit.index, oHit[0].length]);"
                + "     if (lHits.length > 500) break;"
                + "   }"
                + "   if (!lHits.length) continue;"
                + "   const oFragment = document.createDocumentFragment();"
                + "   let iAt = 0;"
                + "   for (const [iStart, iLength] of lHits) {"
                + "     if (iStart > iAt)"
                + "       oFragment.appendChild(document.createTextNode(sText.slice(iAt, iStart)));"
                + "     const elMark = document.createElement('span');"
                + "     elMark.setAttribute('data-homerviewfind', '1');"
                + "     elMark.textContent = sText.substr(iStart, iLength);"
                + "     oFragment.appendChild(elMark);"
                + "     iAt = iStart + iLength;"
                + "     iFound += 1;"
                + "   }"
                + "   if (iAt < sText.length)"
                + "     oFragment.appendChild(document.createTextNode(sText.slice(iAt)));"
                + "   oNode.parentNode.replaceChild(oFragment, oNode);"
                + " }"
                + " return String(iFound);"
                + "})()";

            string sAnswer = EvaluateText(sScript);
            if (sAnswer == null || sAnswer.StartsWith("ERROR:"))
                return "{\"error\":\"The page could not be searched.\"}";
            if (sAnswer.StartsWith("BAD: "))
                return "{\"error\":" + Quote("That regular expression is not valid. "
                    + sAnswer.Substring(5)) + "}";
            Log("  marked " + sAnswer + " matches for " + Abbreviate(sNeedle, 60));
            return "{\"value\":" + Quote(sAnswer) + "}";
        }

        /// <summary>
        /// Every match of a regular expression, run together for reading.
        ///
        /// His separator: line feed, form feed, line feed, written with CRLF
        /// for Windows, so the matches read as pages rather than as a list and
        /// anything that understands a form feed can page through them.
        /// </summary>
        private static string ExtractPattern(string sNeedle)
        {
            if (string.IsNullOrEmpty(sNeedle))
                return "{\"error\":\"No pattern was given.\"}";
            string sScript =
                "(() => {"
                + " let oRe;"
                + " try { oRe = new RegExp(" + Quote(sNeedle) + ", 'gi'); }"
                + " catch (error) { return 'BAD: ' + error.message; }"
                + " const sText = document.body ? document.body.innerText : '';"
                + " const lOut = [];"
                + " let oHit;"
                + " while ((oHit = oRe.exec(sText)) !== null) {"
                + "   if (oHit[0] === '') { oRe.lastIndex += 1; continue; }"
                + "   lOut.push(oHit[0]);"
                + "   if (lOut.length > 2000) break;"
                + " }"
                + " return lOut.join('\\u0001');"
                + "})()";
            string sAnswer = EvaluateText(sScript);
            if (sAnswer == null || sAnswer.StartsWith("ERROR:"))
                return "{\"error\":\"The page could not be searched.\"}";
            if (sAnswer.StartsWith("BAD: "))
                return "{\"error\":" + Quote("That regular expression is not valid. "
                    + sAnswer.Substring(5)) + "}";
            if (sAnswer == "")
                return "{\"error\":\"Nothing on this page matches that.\"}";
            string[] lHits = sAnswer.Split('\u0001');
            // \r\n\f\r\n between matches, as he specified.
            string sJoined = string.Join("\r\n\f\r\n", lHits);
            Log("  extracted " + lHits.Length.ToString() + " matches, "
                + sJoined.Length.ToString() + " characters");
            return "{\"value\":" + Quote(lHits.Length.ToString()
                + (lHits.Length == 1 ? " match." : " matches.") + "\r\n\r\n" + sJoined) + "}";
        }

        private static string ClipboardFile(string sPath)
        {
            if (string.IsNullOrEmpty(sPath))
                return "{\"error\":\"No file was named.\"}";
            if (!File.Exists(sPath))
                return "{\"error\":" + Quote("There is no file at " + sPath) + "}";
            try
            {
                // PORTED FROM Homer.Util.path2Clipboard, LINE FOR LINE.
                //
                // Three hypotheses failed here before the source was read, and
                // the source explains all three. FileDir's clipboard2Path does
                //     MemoryStream stream = (MemoryStream) data.GetData(
                //         "Preferred DropEffect", true);
                //     byte[] aBytes = new byte[] {(byte) stream.ReadByte(), ...
                // and it does NOT check whether stream is null. A clipboard
                // without a Preferred DropEffect therefore threw a null
                // reference, which is what "Unexpected event" was. The earlier
                // attempt that added text but no DropEffect could not have
                // worked, and the one that dropped the text made EdSharp say
                // "No text", correctly, because EdSharp reads the text format.
                //
                // All three go on together: file drop, DropEffect, and the
                // paths as text. 5 means copy; 2 would mean cut.
                string[] lPaths = new string[] { sPath };
                System.Windows.Forms.IDataObject oData =
                    new System.Windows.Forms.DataObject(
                        System.Windows.Forms.DataFormats.FileDrop, lPaths);
                MemoryStream oEffect = new MemoryStream(4);
                byte[] lEffect = new byte[] { 5, 0, 0, 0 };
                oEffect.Write(lEffect, 0, lEffect.Length);
                oData.SetData("Preferred DropEffect", oEffect);
                oData.SetData(string.Join("\r\n", lPaths).Trim());
                System.Windows.Forms.Clipboard.SetDataObject(oData, true);
                // AND THEN LOOK. This said "The file is on the clipboard"
                // without ever asking whether it was, which is the fault this
                // project keeps making. Reading it back costs nothing and puts
                // the formats in the log, so the next report of "the clipboard
                // is wrong" arrives with evidence instead of a symptom.
                Log("  clipboard now holds: " + ClipboardFormats());
                return "{\"value\":\"The file is on the clipboard.\"}";
            }
            catch (Exception exception)
            {
                return "{\"error\":" + Quote(exception.Message) + "}";
            }
        }

        // Puts plain text on the clipboard. The fallback when a file drop is
        // refused, and useful on its own.
        private static string ClipboardText(string sText)
        {
            if (sText == null)
                sText = "";
            try
            {
                if (sText == "")
                    System.Windows.Forms.Clipboard.Clear();
                else
                    System.Windows.Forms.Clipboard.SetText(sText);
                Log("  clipboard now holds: " + ClipboardFormats());
                return "{\"value\":\"The text is on the clipboard.\"}";
            }
            catch (Exception exception)
            {
                return "{\"error\":" + Quote(exception.Message) + "}";
            }
        }

        private static string Launch(string sStartUrl)
        {
            // Already there? Then this is a reconnect, which is the ordinary
            // case: a user presses the launch key to come back to the window.
            if (ReadPort())
            {
                try
                {
                    string sExisting = HttpGet("/json/version");
                    if (sExisting.Contains("webSocketDebuggerUrl"))
                        return "{\"launched\":false,\"connected\":true}";
                }
                catch (Exception)
                {
                    // A port file left behind by a browser that has since
                    // closed. Falling through launches a new one.
                }
            }

            string sEdge = FindEdge();
            Log("  edge:        " + (sEdge == null ? "NOT FOUND" : sEdge));
            if (sEdge == null)
                return "{\"error\":\"Microsoft Edge was not found\"}";

            // Its own profile folder. Since Edge 136 the debugging switches are
            // ignored when the browser uses its normal profile, so a copy
            // sharing that profile could not be spoken to at all.
            string sProfile = ProfileFolder();
            Directory.CreateDirectory(sProfile);

            // A stale port file would be read as proof that a browser is up.
            try
            {
                if (File.Exists(PortFilePath()))
                    File.Delete(PortFilePath());
            }
            catch (Exception)
            {
            }

            // THE SAME SWITCHES THE NVDA SIDE USES, in the same order.
            //
            // They are not decoration. Between them they stop Edge signing in,
            // offering to sign in, checking whether it is the default browser,
            // updating its components, running its first-run experience, and
            // relaunching itself through a compatibility layer, which is one of
            // the ways the process that was started disappears from under us.
            // Launching with a handful of them instead produced a window with a
            // tab open for every extension in the profile and no start page,
            // because the two sides share one profile and only one of them was
            // keeping it quiet.
            //
            // An unrecognised feature name is ignored rather than rejected, so
            // listing several spellings of Edge's sign-in feature is safe.
            string sArguments =
                "--disable-client-side-phishing-detection" +
                " --disable-component-update" +
                " --disable-default-apps" +
                " --disable-features=msImplicitSignin,msEdgeImplicitSignin,EdgeAutoSignIn," +
                "SyncPromo,SigninPromo,PrivacySandboxSettings4,SearchEngineChoiceScreen" +
                " --metrics-recording-only" +
                " --no-default-browser-check" +
                " --no-first-run" +
                " --no-service-autorun" +
                " --edge-skip-compat-layer-relaunch" +
                // --test-type SILENCES THE INFOBAR, and that is all it is here for.
                //
                // Chromium shows "You're using an unsupported command-line flag"
                // for --disable-blink-features, and it has appeared in every
                // session since that flag was added. --test-type is the switch
                // that suppresses the bad-flags infobar. It suppresses OTHER
                // bad-flag warnings too, which would be a real cost in a browser
                // somebody else configured -- here every flag on this line is
                // chosen deliberately a few lines above, so there is nothing else
                // for it to hide.
                //
                // The alternative was dropping --disable-blink-features. That one
                // exists because remote debugging makes navigator.webdriver true
                // and some sign-in pages refuse an automated browser, while this
                // browser really is being driven by a person at a keyboard.
                // Silencing the warning keeps the flag and the quiet both.
                " --test-type" +
                " --disable-blink-features=AutomationControlled" +
                " --remote-debugging-port=0" +
                " --remote-debugging-address=127.0.0.1" +
                " --user-data-dir=\"" + sProfile + "\"" +
                " --new-window" +
                " \"" + (string.IsNullOrEmpty(sStartUrl) ? StartPageUrl() : sStartUrl) + "\"";

            Log("  launching:   " + sEdge + " " + sArguments);
            var startInfo = new ProcessStartInfo
            {
                Arguments = sArguments,
                FileName = sEdge,
                UseShellExecute = false,
            };
            Process.Start(startInfo);

            // Wait for it to answer rather than for a fixed time. The process
            // that was started may exit and hand off to another, so whether it
            // is alive says nothing; whether the port answers says everything.
            for (int iTry = 0; iTry < 100; iTry++)
            {
                Thread.Sleep(100);
                if (!ReadPort())
                    continue;
                try
                {
                    if (HttpGet("/json/version").Contains("webSocketDebuggerUrl"))
                        return "{\"launched\":true,\"connected\":true}";
                }
                catch (Exception)
                {
                }
            }
            return "{\"error\":\"the browser started but never answered\"}";
        }

        private static string FindEdge()
        {
            foreach (string sFolder in new[]
            {
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            })
            {
                string sPath = Path.Combine(sFolder, @"Microsoft\Edge\Application\msedge.exe");
                if (File.Exists(sPath))
                    return sPath;
            }
            return null;
        }

        // --- The two halves of the protocol ----------------------------------

        private static string HttpGet(string sPath)
        {
            var request = (HttpWebRequest)WebRequest.Create(
                "http://127.0.0.1:" + iDebugPort + sPath);
            request.Timeout = 5000;
            using (var response = request.GetResponse())
            using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
                return reader.ReadToEnd();
        }

        private static string Evaluate(string sJavaScript)
        {
            string sSocketUrl = FindActivePageSocket();
            if (sSocketUrl == null)
                return "{\"error\":\"no page to evaluate in\"}";

            string sMessage =
                "{\"id\":1,\"method\":\"Runtime.evaluate\",\"params\":{" +
                "\"expression\":" + Quote(sJavaScript) + "," +
                "\"returnByValue\":true,\"awaitPromise\":true}}";
            return SendAndWait(sSocketUrl, sMessage);
        }

        // The same as evaluate, but the answer is the VALUE, in plain text.
        //
        // The scripting language has no JSON of its own — not one function in
        // the whole reference — so every JSON answer has to be taken apart by
        // hand, character by character, in a loop. That is bearable for a
        // sentence and hopeless for a page: an extracted article is fifty
        // thousand characters and the loop would run fifty thousand times.
        //
        // So the taking apart happens here, where a runtime exists, and the
        // scripts get what they asked for and nothing else. A failure comes
        // back as a line beginning ERROR:, which one comparison detects.
        private static string EvaluateText(string sJavaScript)
        {
            string sAnswer = Evaluate(sJavaScript);
            if (sAnswer == null)
                return "ERROR: nothing came back.";

            // WAS THREE REGULAR EXPRESSIONS, which is a JSON parser written by
            // hand and not a good one: the pattern that reached inside
            // result.result stopped at the first closing brace, so any value
            // that was itself an object came back wrong rather than not at all.
            // .NET reads the JSON now, and XPath asks for the field.
            string sXml = JsonToXml(sAnswer);
            if (sXml == null)
                return "ERROR: the answer could not be read.";

            // A page that throws says so in exceptionDetails, and that is the
            // sentence worth showing. The old code looked for a description
            // anywhere in the text and could find one belonging to something
            // else entirely.
            string sThrown = XmlText(sXml, "/root/result/exceptionDetails/exception/description");
            if (sThrown == "")
                sThrown = XmlText(sXml, "/root/result/exceptionDetails/text");
            if (sThrown != "")
                return "ERROR: " + sThrown;

            // A protocol level refusal, which is a different thing again.
            string sProtocol = XmlText(sXml, "/root/error/message");
            if (sProtocol != "")
                return "ERROR: " + sProtocol;

            XmlDocument oDocument = new XmlDocument();
            try { oDocument.LoadXml(sXml); }
            catch { return "ERROR: the answer could not be read."; }
            XmlNode oValue = oDocument.SelectSingleNode("/root/result/result/value");
            if (oValue != null)
                return oValue.InnerText;
            // undefined has no value field at all, which is not an error: a
            // command that only acts on the page returns nothing by design.
            if (XmlText(sXml, "/root/result/result/type") == "undefined")
                return "";
            return "ERROR: the answer could not be read.";
        }

        private static string Unescape(string sText)
        {
            var builder = new StringBuilder(sText.Length);
            for (int i = 0; i < sText.Length; i++)
            {
                if (sText[i] != '\\' || i + 1 >= sText.Length)
                {
                    builder.Append(sText[i]);
                    continue;
                }
                i++;
                switch (sText[i])
                {
                    case 'n': builder.Append("\r\n"); break;
                    case 'r': break;
                    case 't': builder.Append('\t'); break;
                    case 'b': break;
                    case 'f': break;
                    case '"': builder.Append('"'); break;
                    case '\\': builder.Append('\\'); break;
                    case '/': builder.Append('/'); break;
                    case 'u':
                        if (i + 4 < sText.Length)
                        {
                            int iCode;
                            if (int.TryParse(sText.Substring(i + 1, 4),
                                System.Globalization.NumberStyles.HexNumber,
                                System.Globalization.CultureInfo.InvariantCulture, out iCode))
                            {
                                builder.Append((char)iCode);
                                i += 4;
                            }
                        }
                        break;
                    default: builder.Append(sText[i]); break;
                }
            }
            return builder.ToString();
        }

        // Extract the readable part of the page, save it, and open it in a tab.
        //
        // THE WHOLE JOB, HERE. The scripts used to ask the page for text and
        // show that, which threw away every link in the article — and a link
        // inside the main content is often the reason for reading it. The NVDA
        // side has always written a document and opened it, so this does the
        // same thing, in the same order, with the same engine.
        //
        // Readability's source is INJECTED AS TEXT rather than as a script
        // element. That survives a page whose content security policy forbids
        // outside scripts, and here it arrives through the debugger in the
        // page's own context, so the policy does not apply at all.
        //
        // The source is cached beside the profile. It is a few hundred
        // kilobytes and does not change between pages, and a reader waiting on
        // a command should not wait on a download twice.
        private const string sReadabilityUrl =
            "https://cdn.jsdelivr.net/npm/@mozilla/readability@0.5.0/Readability.js";
        private const string sReadabilityUrlSpare =
            "https://unpkg.com/@mozilla/readability@0.5.0/Readability.js";

        private static string ReadabilitySource()
        {
            string sCache = Path.Combine(
                Directory.GetParent(ProfileFolder()).FullName, "cache", "Readability.js");
            try
            {
                if (File.Exists(sCache) && new FileInfo(sCache).Length > 10000)
                    return File.ReadAllText(sCache);
            }
            catch (Exception)
            {
            }
            foreach (string sUrl in new[] { sReadabilityUrl, sReadabilityUrlSpare })
            {
                try
                {
                    ServicePointManager.SecurityProtocol =
                        SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11 | SecurityProtocolType.Tls;
                    var request = (HttpWebRequest)WebRequest.Create(sUrl);
                    request.Timeout = 30000;
                    request.UserAgent = "HomerView";
                    using (var response = (HttpWebResponse)request.GetResponse())
                    using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
                    {
                        string sSource = reader.ReadToEnd();
                        if (sSource.Length > 10000)
                        {
                            try
                            {
                                Directory.CreateDirectory(Path.GetDirectoryName(sCache));
                                File.WriteAllText(sCache, sSource, new UTF8Encoding(false));
                            }
                            catch (Exception)
                            {
                            }
                            return sSource;
                        }
                    }
                }
                catch (Exception exception)
                {
                    Log("  readability from " + sUrl + " failed: " + exception.Message);
                }
            }
            return "";
        }

        // The fields come back separated by a character no page contains, so
        // one evaluation carries all of them and nothing has to be parsed out
        // of a structure this has to agree with the page about.
        private const string sFieldMark = "\u0001";

        private static string Extract()
        {
            string sSource = ReadabilitySource();
            if (sSource != "")
            {
                Log("  injecting Readability, " + sSource.Length + " characters");
                Evaluate(sSource);
            }

            string sScript =
                "(() => {"
                + "const mark = String.fromCharCode(1);"
                + "if (typeof Readability !== 'undefined') {"
                + "  try {"
                + "    const d = new Readability(document.cloneNode(true)).parse();"
                + "    if (d && d.content && d.length > 200)"
                + "      return [d.title || document.title, d.byline || '', d.siteName || '',"
                + "        String(d.length), 'Readability', d.content].join(mark);"
                + "  } catch (e) { }"
                + "}"
                + "let elBest = null, nBest = 0;"
                + "for (const el of document.querySelectorAll('main,[role=main],article,section,div,td')) {"
                + "  const s = (el.innerText || '').trim();"
                + "  if (s.length < 200) continue;"
                + "  let iLink = 0;"
                + "  for (const a of el.querySelectorAll('a')) iLink += (a.innerText || '').length;"
                + "  const nShare = iLink / s.length;"
                + "  if (nShare > 0.5) continue;"
                + "  let n = s.length * (1 - nShare);"
                + "  if (el.tagName === 'MAIN') n *= 2;"
                + "  if (el.tagName === 'ARTICLE') n *= 1.5;"
                + "  if (n > nBest) { nBest = n; elBest = el; }"
                + "}"
                + "if (!elBest) return '';"
                + "return [document.title, '', location.hostname,"
                + "  String(elBest.innerText.length), 'weighing the page', elBest.innerHTML].join(mark);"
                + "})()";

            string sAnswer = EvaluateText(sScript);
            if (sAnswer.StartsWith("ERROR:"))
                return "{\"error\":" + Quote(sAnswer) + "}";
            if (sAnswer.Trim() == "")
                return "{\"error\":\"No main content could be identified on this page.\"}";

            string[] lFields = sAnswer.Split(new[] { sFieldMark }, StringSplitOptions.None);
            if (lFields.Length < 6)
                return "{\"error\":\"The extraction came back in a shape this did not expect.\"}";
            string sTitle = lFields[0];
            string sByline = lFields[1];
            string sSite = lFields[2];
            string sLength = lFields[3];
            string sMethod = lFields[4];
            string sContent = lFields[5];
            string sPageUrl = EvaluateText("location.href");
            if (sPageUrl.StartsWith("ERROR:"))
                sPageUrl = "";

            var builder = new StringBuilder();
            builder.Append("<!doctype html>\r\n<html lang=\"en\">\r\n<head>\r\n");
            builder.Append("<meta charset=\"utf-8\">\r\n");
            builder.Append("<title>" + EscapeHtml(sTitle) + "</title>\r\n");
            builder.Append("</head>\r\n<body>\r\n<header>\r\n");
            builder.Append("<h1>" + EscapeHtml(sTitle) + "</h1>\r\n");
            if (sByline != "")
                builder.Append("<p>" + EscapeHtml(sByline) + "</p>\r\n");
            if (sSite != "")
                builder.Append("<p>" + EscapeHtml(sSite) + "</p>\r\n");
            if (sPageUrl != "")
                builder.Append("<p><a href=\"" + EscapeHtml(sPageUrl) + "\">The page this came from</a></p>\r\n");
            builder.Append("<p>Extracted by " + EscapeHtml(sMethod) + ".</p>\r\n");
            builder.Append("</header>\r\n<main>\r\n");
            builder.Append(sContent);
            builder.Append("\r\n</main>\r\n</body>\r\n</html>\r\n");

            string sFolder = Path.Combine(
                Directory.GetParent(ProfileFolder()).FullName, "temp");
            string sDocument = Path.Combine(sFolder, "MainContent.htm");
            try
            {
                Directory.CreateDirectory(sFolder);
                File.WriteAllText(sDocument, builder.ToString(), new UTF8Encoding(true));
            }
            catch (Exception exception)
            {
                return "{\"error\":" + Quote("The document could not be saved: " + exception.Message) + "}";
            }
            Log("  wrote " + sDocument + ", " + new FileInfo(sDocument).Length + " bytes");

            // A tab, opened through the debugger rather than by the page.
            // window.open from a page to a file address is refused by the
            // browser, which is why the page cannot be asked to do this.
            string sOpened = OpenInTab(new Uri(sDocument).AbsoluteUri);

            return "{\"value\":" + Quote(
                "Main content extracted by " + sMethod + ", " + sLength
                + " characters, " + sOpened + "\r\n" + sDocument) + "}";
        }

        // The open tabs, as lines rather than as a protocol answer.
        //
        // The scripts could be handed the raw list and made to pick it apart,
        // but that is the per-character loop again, and this side has a
        // runtime. One line per tab, the title then the address.
        private static string TabList()
        {
            string sList = HttpGet("/json/list");
            var lLines = new List<string>();
            int iCount = 0;
            foreach (Match match in Regex.Matches(sList, "\\{[^{}]*?\"type\"\\s*:\\s*\"page\"[^{}]*?\\}"))
            {
                if (match.Value.Contains("devtools://"))
                    continue;
                Match matchTitle = Regex.Match(match.Value,
                    "\"title\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
                Match matchUrl = Regex.Match(match.Value,
                    "\"url\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
                Match matchId = Regex.Match(match.Value,
                    "\"id\"\\s*:\\s*\"([^\"]+)\"");
                iCount += 1;
                // ONE RECORD PER TAB, fields separated by a tab and records by
                // character 7 -- the same separator dialogPick uses. The
                // scripts turn each into a LINK, so Enter on a title activates
                // that tab, which is what a JAWS user expects of a list.
                // Building a paragraph of text here instead would have thrown
                // the target id away, and the id is the only thing that can
                // activate anything.
                lLines.Add((matchId.Success ? matchId.Groups[1].Value : "")
                    + "\t" + (matchTitle.Success
                        ? Unescape(matchTitle.Groups[1].Value) : "no title")
                    + "\t" + (matchUrl.Success
                        ? Unescape(matchUrl.Groups[1].Value) : ""));
            }
            if (iCount == 0)
                return "{\"error\":\"No tabs are open.\"}";
            return "{\"value\":" + Quote(string.Join("\a", lLines.ToArray())) + "}";
        }

        private static string EscapeHtml(string sText)
        {
            return (sText ?? "").Replace("&", "&amp;").Replace("<", "&lt;")
                .Replace(">", "&gt;").Replace("\"", "&quot;");
        }

        // A new tab, asked of the browser itself rather than of a page.
        private static string OpenInTab(string sUrl)
        {
            try
            {
                string sVersion = HttpGet("/json/version");
                Match match = Regex.Match(sVersion,
                    "\"webSocketDebuggerUrl\"\\s*:\\s*\"([^\"]+)\"");
                if (!match.Success)
                    return "but no tab could be opened.";
                string sMessage =
                    "{\"id\":1,\"method\":\"Target.createTarget\",\"params\":{\"url\":"
                    + Quote(sUrl) + "}}";
                SendAndWait(match.Groups[1].Value, sMessage);
                return "opened in a new tab.";
            }
            catch (Exception exception)
            {
                Log("  the tab could not be opened: " + exception.Message);
                return "but no tab could be opened.";
            }
        }

        /// <summary>
        /// The socket of the tab the reader is actually in.
        ///
        /// THIS USED TO RETURN THE FIRST PAGE IN THE LIST, with a comment
        /// saying that which tab has focus was a question for a later version
        /// and that the common case is one tab. The common case stopped being
        /// one tab as soon as Extract Main Content began opening its own, and
        /// the consequence was not silence but a WRONG ANSWER given
        /// confidently: with three tabs open, Say Metadata described
        /// HomerView's own start page while the reader was on ollama.com, and
        /// nothing in the answer suggested it was about a different page.
        ///
        /// document.hasFocus() is true in exactly one tab of the focused
        /// window, so each candidate is simply asked. With one page target
        /// there is nothing to decide and nothing is asked. If no tab claims
        /// focus -- which happens when Edge is not the foreground window at
        /// all -- the first is used, and the log says that is what happened,
        /// because a fallback nobody can see is how this went unnoticed.
        /// </summary>
        private static string FindActivePageSocket()
        {
            var lSockets = new List<string>();
            string sList = HttpGet("/json/list");
            foreach (Match match in Regex.Matches(sList,
                "\\{[^{}]*?\"type\"\\s*:\\s*\"page\"[^{}]*?\\}"))
            {
                Match matchSocket = Regex.Match(match.Value,
                    "\"webSocketDebuggerUrl\"\\s*:\\s*\"([^\"]+)\"");
                if (!matchSocket.Success)
                    continue;
                if (match.Value.Contains("devtools://"))
                    continue;
                lSockets.Add(matchSocket.Groups[1].Value);
            }
            if (lSockets.Count == 0)
                return null;
            if (lSockets.Count == 1)
                return lSockets[0];

            Log("  " + lSockets.Count.ToString() + " tabs are open, asking which has focus");
            foreach (string sSocket in lSockets)
            {
                try
                {
                    string sAnswer = SendAndWait(sSocket,
                        "{\"id\":1,\"method\":\"Runtime.evaluate\",\"params\":{"
                        + "\"expression\":\"document.hasFocus()\",\"returnByValue\":true}}");
                    if (sAnswer != null && sAnswer.Contains("\"value\":true"))
                    {
                        Log("  using the tab that has focus");
                        return sSocket;
                    }
                }
                catch (Exception oError)
                {
                    Log("  a tab could not be asked: " + oError.Message);
                }
            }
            Log("  NO TAB HAS FOCUS, so the first is used and the answer may be about another page");
            return lSockets[0];
        }

        private static int iCallBudgetSeconds = iCallTimeoutSeconds;

        private static string SendAndWait(string sSocketUrl, string sMessage)
        {
            // A CANCELLATION TOKEN IS NOT ENOUGH ON ITS OWN.
            //
            // The IBM engine ran on a large page and the whole thing stopped:
            // no answer, no timeout message, no exception in the log, and JAWS
            // held for as long as anyone was willing to wait. The token was set
            // to twenty seconds and never fired, because ClientWebSocket's
            // ReceiveAsync on .NET Framework does not reliably observe a token
            // once it is blocked on the socket.
            //
            // So every wait is now bounded TWICE: by the token, and by waiting
            // on the task itself with a deadline. The second one cannot be
            // ignored. A command that cannot finish must still return, because
            // the scripts wait for this process and a process that never exits
            // is a screen reader that never comes back.
            DateTime oDeadline = DateTime.UtcNow.AddSeconds(iCallBudgetSeconds);
            using (var socket = new ClientWebSocket())
            using (var cancellation = new CancellationTokenSource(
                TimeSpan.FromSeconds(iCallBudgetSeconds)))
            {
                socket.ConnectAsync(new Uri(sSocketUrl), cancellation.Token)
                    .GetAwaiter().GetResult();

                byte[] bMessage = Encoding.UTF8.GetBytes(sMessage);
                socket.SendAsync(new ArraySegment<byte>(bMessage),
                    WebSocketMessageType.Text, true, cancellation.Token)
                    .GetAwaiter().GetResult();

                // The browser sends events as well as replies, and they arrive
                // in whatever order it likes. So read until the reply carrying
                // our own id turns up rather than taking the first thing said.
                var lBuffer = new byte[64 * 1024];
                var builder = new StringBuilder();
                while (!cancellation.IsCancellationRequested)
                {
                    builder.Clear();
                    WebSocketReceiveResult result;
                    do
                    {
                        int iLeft = (int) (oDeadline - DateTime.UtcNow).TotalMilliseconds;
                        if (iLeft <= 0)
                            return "{\"error\":\"The browser did not answer in "
                                + iCallBudgetSeconds.ToString() + " seconds.\"}";
                        var oReceive = socket.ReceiveAsync(
                            new ArraySegment<byte>(lBuffer), cancellation.Token);
                        if (!oReceive.Wait(iLeft))
                            return "{\"error\":\"The browser did not answer in "
                                + iCallBudgetSeconds.ToString() + " seconds.\"}";
                        result = oReceive.Result;
                        builder.Append(Encoding.UTF8.GetString(lBuffer, 0, result.Count));
                    }
                    while (!result.EndOfMessage);

                    string sReply = builder.ToString();
                    if (Regex.IsMatch(sReply, "^\\s*\\{\\s*\"id\"\\s*:\\s*1\\b"))
                        return sReply;
                    if (DateTime.UtcNow >= oDeadline)
                        break;
                }
                return "{\"error\":\"The browser did not answer in "
                    + iCallBudgetSeconds.ToString() + " seconds.\"}";
            }
        }

        // --- Writing the answer ----------------------------------------------


        // --- JSON in, XML out -----------------------------------------------

        /// <summary>
        /// Turns a JSON answer into XML, so the scripting language can read it
        /// with the XML functions it actually has.
        ///
        /// JSL HAS NO JSON FUNCTIONS AT ALL -- not one in the seventeen hundred
        /// odd names the reference documents. It has a full XML side instead,
        /// because the off screen model is XML: CreateXMLDomDoc, then
        /// LoadAndParseXML, and the document answers XPath. So the reliable
        /// direction is to hand it XML.
        ///
        /// NOTHING HERE PARSES ANYTHING. JsonReaderWriterFactory is .NET's own
        /// JSON reader, presented as an XmlReader, and the mapping it uses is
        /// documented and lossless: every object becomes an element, every
        /// array member becomes an item element, and each carries a type
        /// attribute saying what it was. Writing a JSON parser by hand -- which
        /// is what the three regular expressions in EvaluateText were -- is how
        /// a nested object silently becomes the wrong answer.
        ///
        /// The one thing that must be done by hand is dropping characters XML
        /// forbids. JSON is content to carry a byte below space; XML 1.0 is
        /// not, and a page that contains one would otherwise produce an answer
        /// the script side cannot parse, on that page only, which is the worst
        /// kind of fault to be handed.
        /// </summary>
        private static string JsonToXml(string sJson)
        {
            if (string.IsNullOrEmpty(sJson))
                return null;
            try
            {
                string sClean = Regex.Replace(sJson, "[\u0000-\u0008\u000B\u000C\u000E-\u001F]", "");
                byte[] lBytes = Encoding.UTF8.GetBytes(sClean);
                using (XmlReader oReader = JsonReaderWriterFactory.CreateJsonReader(
                    lBytes, new XmlDictionaryReaderQuotas()))
                {
                    XmlDocument oDocument = new XmlDocument();
                    oDocument.Load(oReader);
                    return oDocument.OuterXml;
                }
            }
            catch (Exception oError)
            {
                Log("  the answer could not be turned into XML: " + oError.Message);
                return null;
            }
        }

        /// <summary>
        /// The value of one XPath expression, or an empty string.
        /// </summary>
        private static string XmlText(string sXml, string sPath)
        {
            try
            {
                XmlDocument oDocument = new XmlDocument();
                oDocument.LoadXml(sXml);
                XmlNode oNode = oDocument.SelectSingleNode(sPath);
                return oNode == null ? "" : oNode.InnerText;
            }
            catch
            {
                return "";
            }
        }

        /// <summary>
        /// Every answer but evaluateText's leaves as XML. If the conversion
        /// fails the original goes out unchanged: an answer in a shape the
        /// caller did not expect is still better than no answer, which reads
        /// as a crash.
        /// </summary>
        private static string XmlAnswer(string sJson)
        {
            string sXml = JsonToXml(sJson);
            return sXml == null ? sJson : sXml;
        }

        private static void WriteResult(string sPath, string sText)
        {
            string sFolder = Path.GetDirectoryName(sPath);
            if (!string.IsNullOrEmpty(sFolder))
                Directory.CreateDirectory(sFolder);
            // UTF-16, BECAUSE THAT IS WHAT THE READING SIDE UNDERSTANDS.
            //
            // This was UTF-8 with a byte order mark, and the scripts open the
            // file with OpenTextFile in its default mode, which knows nothing
            // of either. The mark arrived as three visible characters in front
            // of the answer, so no XML would parse and every non-ASCII
            // character was mojibake besides.
            //
            // OpenTextFile's fourth argument asks for Unicode, the
            // FileSystemObject then reads UTF-16 and swallows the mark itself,
            // and accented text survives. The two sides must be changed
            // together, which is why check 13 exists.
            File.WriteAllText(sPath, sText.Replace("\n", "\r\n"),
                new UnicodeEncoding(false, true));
        }

        private static string Quote(string sText)
        {
            var builder = new StringBuilder("\"");
            foreach (char cCharacter in sText ?? "")
            {
                switch (cCharacter)
                {
                    case '"': builder.Append("\\\""); break;
                    case '\\': builder.Append("\\\\"); break;
                    case '\n': builder.Append("\\n"); break;
                    case '\r': builder.Append("\\r"); break;
                    case '\t': builder.Append("\\t"); break;
                    default:
                        if (cCharacter < 32)
                            builder.Append("\\u").Append(((int)cCharacter).ToString("x4"));
                        else
                            builder.Append(cCharacter);
                        break;
                }
            }
            return builder.Append("\"").ToString();
        }
    }
}
