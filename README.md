# Kisap

Kisap, formerly Tachiyomi Lite, is a lightweight manga reader built as an unofficial performance overlay for [Mihon](https://github.com/mihonapp/mihon). It targets lower-memory Android phones such as the Samsung Galaxy A16 5G with 4 GB RAM.

## Reader features

- **Auto Lite Mode** on devices reporting < 5 GiB of physical RAM. Overrides are available in Reader Settings → Lite.
- **Bounded network prefetch:** read the visible page first, preload fewer surrounding pages and use smaller download chunks when Lite Mode is on.
- **Smaller Webtoon view cache** and cached-view trimming after Android low-memory signals.
- **WebView return recovery:** retry nearby failed chapter pages after the built-in chapter WebView is closed. This **does not bypass Cloudflare/CAPTCHA**.
- **Manual retry:** in Reader Settings → Lite, tap **Retry nearby failed pages** after completing verification.
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

The Tachiyomi Lite v0.2 ARM64 APK built successfully on GitHub Actions. The smoke tests check the overlay's source anchors and branding resource references. GitHub Actions runs the full Android compile check for each build.

Source licensing: Mihon is Apache-2.0 licensed. This overlay is also Apache-2.0, without official endorsement or affiliation.
