# 📱 SafeRoute como aplicativo (Android, iOS e PC)

Existem **três caminhos** para transformar o SafeRoute em "aplicativo de
verdade", do mais simples ao mais elaborado. Você não precisa fazer todos —
escolha conforme o esforço que quer investir.

---

## 1️⃣ PWA (Progressive Web App) — JÁ ESTÁ PRONTO

O SafeRoute já é um PWA. Só precisa instalar.

### iPhone / iPad (Safari)
1. Abra https://saferoute-rqcj.onrender.com no Safari (não Chrome)
2. Toque no botão **Compartilhar** (□↑) na barra inferior
3. Role e toque em **"Adicionar à Tela de Início"**
4. Confirme. Pronto — vira ícone na home como qualquer app

### Android (Chrome)
1. Abra https://saferoute-rqcj.onrender.com no Chrome
2. Vai aparecer um banner "Adicionar SafeRoute à tela inicial"
3. Aceite. Se não aparecer, menu ⋮ → **"Instalar app"**

### Windows / macOS / Linux (Chrome ou Edge)
1. Abra a URL no Chrome ou Edge
2. Na barra de endereço, ícone **⊕** (Instalar SafeRoute)
3. Vira janela própria, com ícone na taskbar/dock

**Vantagens:** zero esforço, atualização automática a cada deploy.
**Limites:** sem notificações push no iOS, sem listagem na App Store/Play Store.

---

## 2️⃣ App nativo via Capacitor (APK + IPA pra publicar nas lojas)

Capacitor envelopa o SafeRoute num WebView nativo, gerando APK (Android) e
IPA (iOS) pra publicar na Play Store e App Store.

### Pré-requisitos
- **Node.js 18+** e **npm**
- Para iOS: **macOS** com Xcode 14+
- Para Android: **Android Studio** com SDK 33+

### Setup (faz uma vez)

```bash
# Cria projeto Capacitor numa pasta separada do backend
mkdir saferoute-mobile && cd saferoute-mobile
npm init -y
npm install @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android
npx cap init SafeRoute com.saferoute.app --web-dir=dist
```

### Edita `capacitor.config.ts` — aponta pro server em produção

```ts
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.saferoute.app',
  appName: 'SafeRoute',
  webDir: 'dist',
  server: {
    url: 'https://saferoute-rqcj.onrender.com',
    cleartext: false
  }
};
export default config;
```

> Como o webDir aponta pro servidor remoto, o app vira um "wrapper" — qualquer
> deploy no Render reflete no app sem precisar republicar APK/IPA.

### Build pra Android

```bash
mkdir dist && echo '<meta http-equiv="refresh" content="0;url=https://saferoute-rqcj.onrender.com">' > dist/index.html
npx cap add android
npx cap open android
# No Android Studio: Build → Generate Signed Bundle / APK
```

### Build pra iOS

```bash
npx cap add ios
npx cap open ios
# No Xcode: Product → Archive → Distribute App
```

### Publicar nas lojas
- **Google Play:** conta de dev = US$ 25 (uma vez). Sobe AAB no Play Console
- **Apple App Store:** US$ 99/ano. Sobe IPA via Xcode → Transporter

---

## 3️⃣ App desktop nativo via Tauri (Windows .exe / macOS .dmg / Linux .AppImage)

Tauri usa Rust + WebView do sistema (muito mais leve que Electron — 5MB vs 150MB).

### Pré-requisitos
- **Rust** (https://rustup.rs)
- **Node.js**

```bash
mkdir saferoute-desktop && cd saferoute-desktop
npm create tauri-app@latest .
# Quando perguntar: framework "Vanilla", language "TypeScript"
```

Edita `src-tauri/tauri.conf.json`:

```json
{
  "build": {
    "devUrl": "https://saferoute-rqcj.onrender.com",
    "frontendDist": "https://saferoute-rqcj.onrender.com"
  },
  "app": {
    "windows": [{ "title": "SafeRoute", "width": 1200, "height": 800 }]
  }
}
```

Build:
```bash
npm run tauri build
# Saída em src-tauri/target/release/bundle/
```

---

## Comparativo rápido

| Solução | Esforço | Custo loja | Tamanho | Atualização |
|---|---|---|---|---|
| **PWA** | Zero | Gratis | 0 (web) | Automática |
| **Capacitor (APK/IPA)** | Médio | Play US$25 + Apple US$99/ano | ~5 MB wrapper | Quase automática (server URL) |
| **Tauri (desktop)** | Médio | Gratis | ~10 MB binário | Automática (server URL) |

**Recomendação para o trabalho de PUC:** começa com **PWA** (já funciona).
Se for apresentar algo "instalável de verdade", parte pra **Capacitor APK** —
em ~2 horas de trabalho você tem um APK assinado pra demonstrar.

---

## Troubleshooting

**"Mapbox não carrega no APK"**
→ Adiciona o domínio `https://saferoute-rqcj.onrender.com` nas
URL restrictions do seu token Mapbox. Sem isso, ele bloqueia o WebView.

**"Geolocation não funciona no Capacitor"**
→ No `AndroidManifest.xml`, adiciona:
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
```
No `Info.plist` do iOS:
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>SafeRoute usa sua localização para sugerir a origem da rota.</string>
```
