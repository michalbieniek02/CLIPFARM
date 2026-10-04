pragma Singleton
import QtQuick

QtObject {
    readonly property color background: "#0d1117"
    readonly property color sidebar: "#121820"
    readonly property color surface: "#19222d"
    readonly property color raised: "#22303d"
    readonly property color hover: "#2a3b4b"
    readonly property color border: "#314253"
    readonly property color text: "#f1f5f8"
    readonly property color muted: "#a6b6c6"
    readonly property color accent: "#0071e3"
    readonly property color accentHover: "#1687f8"
    readonly property color teal: "#2ab8a8"
    readonly property color green: "#9ac74c"
    readonly property color orange: "#ff930d"
    readonly property color danger: "#ff8f8b"
    readonly property color focus: "#62b5ff"
    readonly property int radius: 14
    readonly property int controlRadius: 9
    readonly property int spacing: 16
    readonly property int margin: 24
    readonly property bool motion: backend.animationsEnabled
    readonly property int fast: motion ? 160 : 0
    readonly property int normal: motion ? 240 : 0
    readonly property int slow: motion ? 300 : 0
    readonly property string fontFamily: Qt.application.font.family
}
