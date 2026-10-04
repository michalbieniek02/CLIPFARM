---
name: CLIPFARM
description: Native Windows studio for turning local films into publishable clips.
colors:
  background: "#0d1117"
  sidebar: "#121820"
  surface: "#19222d"
  raised: "#22303d"
  hover: "#2a3b4b"
  border: "#314253"
  text: "#f1f5f8"
  muted: "#a6b6c6"
  accent: "#0071e3"
  accent-hover: "#1687f8"
  teal: "#2ab8a8"
  green: "#9ac74c"
  orange: "#ff930d"
  danger: "#ff8f8b"
  focus: "#62b5ff"
typography:
  headline: {fontFamily: "Inter, Segoe UI", fontSize: "30px", fontWeight: 600}
  title: {fontFamily: "Inter, Segoe UI", fontSize: "21px", fontWeight: 600}
  clip-title: {fontFamily: "Inter, Segoe UI", fontSize: "16px", fontWeight: 600}
  body: {fontFamily: "Inter, Segoe UI", fontSize: "13px", fontWeight: 400}
  button: {fontFamily: "Inter, Segoe UI", fontSize: "13px", fontWeight: 600}
  label: {fontFamily: "Inter, Segoe UI", fontSize: "10px", letterSpacing: "1px"}
  metadata: {fontFamily: "Inter, Segoe UI", fontSize: "11px"}
  log: {fontFamily: "Consolas", fontSize: "12px"}
rounded:
  panel: "14px"
  control: "9px"
  segment: "6px"
spacing:
  inline: "8px"
  compact: "12px"
  standard: "16px"
  card: "18px"
  margin: "24px"
components:
  button-primary: {backgroundColor: "{colors.accent}", textColor: "{colors.text}", typography: "{typography.button}", rounded: "{rounded.control}", height: "40px"}
  button-primary-hover: {backgroundColor: "{colors.accent-hover}"}
  button-secondary: {backgroundColor: "{colors.surface}", textColor: "{colors.text}", typography: "{typography.button}", rounded: "{rounded.control}", height: "40px"}
  button-secondary-hover: {backgroundColor: "{colors.hover}"}
  field: {backgroundColor: "{colors.raised}", textColor: "{colors.text}", typography: "{typography.body}", rounded: "{rounded.control}", padding: "12px", height: "38px"}
  card: {backgroundColor: "{colors.surface}", textColor: "{colors.text}", rounded: "{rounded.panel}", padding: "{spacing.card}"}
  segment-track: {backgroundColor: "{colors.raised}", rounded: "{rounded.control}", padding: "4px", height: "40px"}
---

# Design System: CLIPFARM

## Overview

**Creative North Star: "Operate — the desktop clip studio"**

CLIPFARM is a calm, dark Windows workbench for making clips from real local media. Settings occupy a stable left rail; video and resulting clips own the main workspace. Polish comes from legible hierarchy, tonal surfaces, a restrained blue action accent, and small transitions that explain changes.

The supplied CLIPFARM artwork remains the identity authority. Use the actual mark from assets in the header and empty states, and locally decoded media thumbnails once a film exists. The user requested this PySide6 / QML world to replace the former light CustomTkinter interface. The existing Python media, Whisper transcription, selection, export, and project workflow remains connected.

**Key Characteristics:**

- Dark, focused Windows desktop workspace.
- Real media, original logo, and clear action hierarchy.
- Independent settings and results scrolling.
- Short state transitions with a complete reduced-motion path.

Normative implementation source: qml/Theme.qml, with component details in qml/*.qml and application font selection in qt_app.py.

## Colors

### Primary
Action Blue (accent) marks substantive actions, active segmented choices, and text selection. Its brighter hover token communicates pointer availability.

### Secondary
Teal supports activity and progress. Orchard Green marks a ready transcript and carries the logo's established green identity.

### Tertiary
Harvest Orange preserves the supplied identity palette; it is available in Theme rather than decorating every surface. Danger identifies destructive text. Focus provides an independent keyboard border.

### Neutral
Background anchors the canvas and log. Sidebar separates settings and toolbar. Surface supports media cards; Raised gives fields and hovered cards a distinct plane. Hover identifies interactive availability. Border divides controls. Text and Muted separate primary from supporting information.

**The Action Rule.** Use blue for actions and selections; retain green, teal, and orange for their established semantic or brand roles.

## Typography

Inter is selected when installed; Segoe UI is the Windows fallback. QML inherits the application font through Theme.fontFamily. Consolas is reserved for the selectable log. Anton belongs to rendered video captions, now sized at 84px for a 1080px canvas (20% larger), with automatic fitting for long phrases. The sidebar does not expose a custom prompt field; clip selection uses the existing engine instructions.

Headline leads the workspace, title heads the clip list, and clip-title identifies individual clips. Body and buttons share a compact size with weight distinguishing actions. Secondary copy uses 12px; panel headings use 22px. Settings headings use uppercase label with tracked letters. Native text rendering handles line height; no custom line-height token is defined.

**The Legibility Rule.** Wrap explanatory copy; truncate filenames and compact status only where the layout provides their full context elsewhere.

## Layout

The default native window is 1360 × 900 with a minimum of 1100 × 780. Toolbar height is 76px. The settings rail is 296px wide; remaining width belongs to a fluid main column using margin and standard gap tokens. This is a desktop minimum-size layout.

Settings scroll independently from the clip ListView. The source card is 224px high empty and 192px with a film. Media preserves aspect ratio. Clip rows adapt height to title and reason text. Export actions, selection count, status, and progress sit below results.

The log slides from the right to a maximum width of 520px. In-app preview is at most 680px wide with a 24px window inset. Both disable background interaction while open.

## Elevation & Depth

Tonal layering carries most depth. Video and clip cards use subtle Qt Quick MultiEffect shadows offset vertically by 3px. Video uses #30000000 with blur 0.3; clips use #28000000 with blur 0.2. These are Qt effect parameters, not CSS shadow lengths. Overlays dim the workspace with #66000000.

**The Quiet Depth Rule.** Keep shadows local to media cards; use surface contrast, borders, and a dimmed backdrop to establish hierarchy elsewhere.

## Shapes

Panels use panel radius and controls the smaller control radius. Segmented selections use segment radius within an inset track. Inputs and secondary buttons have one-pixel borders; focused inputs and buttons use two-pixel Focus borders. Score badges have 7px corners. Switches use capsule tracks.

## Components

### Buttons
Primary uses Action Blue; secondary uses Surface and Border. Hover uses accent-hover or Hover. Pressed primary uses #005dbd; pressed secondary uses Raised. Press shrinks buttons to 0.97 when motion is enabled. Disabled buttons use opacity 0.42. Destructive actions use Danger text. Compact row actions are 32px high and status actions 30px.

### Inputs / Fields
Fields use Raised, Text, Muted placeholders, and control radius. Focus increases border width and uses Focus. Disabled fields and choices use opacity 0.45. Choice menus are QML popups with Surface, Border, rounded corners, and highlighted hover rows.

### Navigation
Header contains original brand artwork and project open/save. Segmented mode and format choices slide a blue selection within a 4px inset track. Unselected labels use Muted. There is no page-navigation sidebar.

### Cards / Containers
Source card accepts a dropped local film. Drag-over changes background to Raised and border to Focus. Transcript state and transcription/import/download actions remain explicit. Busy state disables source changes.

Clip rows show real thumbnails, selection, title, reason, timestamps, and preview/edit/delete. Hover lifts a row 2px when motion is enabled. Positive scores use a compact #154034 badge with #b8eaa4 text.

### Task status and motion
Busy indicators accompany readable status. Determinate progress displays its value; indeterminate progress uses activity motion. Theme defines fast (160ms), normal (240ms), slow (300ms), all resolving to zero with animations disabled. State fades, segment movement, reveals, and panel slides use these tokens, generally with Qt OutCubic for movement. Reveal delays use 45ms steps capped at six rows. Spinner rotation uses 950ms; progress loops use 1200/1300ms and stop with backend.animationsEnabled false.

Windows client-area animation preference drives the backend reduced-motion policy. CLIPFARM_REDUCED_MOTION provides a test override. Slow is available as a theme token; do not assume every motion duration is used by the current components.

### Details and video preview
Szczegóły opens a sliding, selectable Consolas task log. Preview uses QtMultimedia MediaPlayer, AudioOutput, and VideoOutput with play/pause, seek, volume, and close.

Opening a panel focuses its close button. Tab and Shift+Tab stay inside the active panel, background controls are disabled, and closing restores the prior enabled focus target. An error can open Details above Preview.

Ctrl+O opens a project. Ctrl+S saves the current project. Both are disabled while busy or a panel is open. Escape closes panels first; otherwise it cancels an active task. Choosing a source film is a separate action.

## Do's and Don'ts

### Do:
- Do retain the supplied logo and actual media thumbnails.
- Do use Theme as token source and preserve the blue action accent.
- Do keep settings and results independently scrollable.
- Do confine focus to open panels and restore it on close.
- Do honor Windows reduced motion for transitions and continuous indicators.
- Do preserve the existing media, transcription, selection, export, and project workflow.

### Don't:
- Don't reintroduce the former light CustomTkinter visual world.
- Don't substitute stock video, a drawn logo, or decorative imagery for real media and identity assets.
- Don't make unavailable actions look enabled.
- Don't use the video-caption font for desktop controls.
- Don't add motion that bypasses backend.animationsEnabled.
