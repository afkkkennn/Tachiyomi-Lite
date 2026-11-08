# Kisap

Kisap, formerly Tachiyomi Lite, is a lightweight manga reader built as an unofficial performance overlay for [Mihon](https://github.com/mihonapp/mihon). It targets lower-memory Android phones such as the Samsung Galaxy A16 5G with 4 GB RAM.

## Phase 3

- **Resume from Library.** Open the last eligible title and continue from its saved reading progress. The shortcut uses recent history and respects downloaded-only mode.
- **Recover from a source check.** Open a failed online page in WebView, complete any verification the site asks for, and return to retry failed pages near your reading position.
- **Source load feedback.** Browse shows when a source failed to load and offers a retry. Earlier results stay visible during a paging error, with error details and WebView available where applicable.
- **One-handed reader controls.** Open Reader Settings → General → Reader controls and choose **Left hand** or **Right hand**. Back, bookmark, and settings move within thumb reach, with reading mode, rotation, and crop grouped under More options.

## Low-memory reader features

- **Auto Lite Mode** on devices reporting < 5 GiB of physical RAM. Overrides are available in Reader Settings → Lite.
- **Bounded network prefetch:** read the visible page first, preload fewer surrounding pages and use smaller download chunks when Lite Mode is on.
- **Smaller Webtoon view cache** and cached-view trimming after Android low-memory signals.
- **Manual retry.** In Reader Settings → Lite, tap **Retry nearby failed pages** after completing verification.
- **Kisap branding** on the launcher and splash screen, with a monochrome launcher icon for system theming. The debug application ID is `app.mihon.dev`.

The source code and settings UI are overlaid onto a pinned upstream Mihon revision during an automated build. The original Mihon repository is not copied into this repository.

## Get an APK

1. Open the [Actions tab](../../actions/workflows/build-tachiyomi-lite.yml).
2. Select **Build Kisap APK** → **Run workflow**, or open the latest automatic push build.
3. After a **successful** workflow run, open **Artifacts** and download `kisap-samsung-a16-apk`.
4. Extract `Kisap-A16-arm64.apk` from the ZIP.

**Do not install an APK from a failed build.** Android may warn about sideloading. Back up your Mihon library before migration. Debug builds aren't production releases and aren't automatically updated.

## Run locally

Requirements: Python 3, Git, JDK 21, Android SDK.

```sh
git clone https://github.com/mihonapp/mihon.git mihon
python3 -m unittest discover -s tests -v
python3 apply_lite.py mihon --check
python3 apply_lite.py mihon
cd mihon
./gradlew :app:assembleDebug --no-daemon
```

For a reproducible build, check out the upstream SHA pinned in `.github/workflows/build-tachiyomi-lite.yml` before patching.

## Build verification

The smoke tests check source anchors, branding resource references, and Phase 3 patch application. GitHub Actions compiles the Android app when changes to the overlay or build workflow enter a pull request.

Source licensing: Mihon is Apache-2.0 licensed. This overlay is also Apache-2.0, without official endorsement or affiliation.
