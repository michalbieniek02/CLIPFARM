import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Rectangle {
    id: root
    objectName: "settingsPreview"
    color: Theme.surface
    radius: Theme.radius
    readonly property bool vertical: backend.settings.format === "Pionowy 9:16"
    readonly property bool fitted: !vertical || backend.settings.framing === "Cały obraz · czarne pasy"
    readonly property real tempo: backend.settings.speed_up ? 1.1 : 1
    readonly property real faceCenter: backend.settings.mirror ? .47 : .53
    property bool playing: true
    property int wordIndex: 3
    readonly property var words: ["TAK", "WYGLĄDA", "TWÓJ", "KLIP"]
    Accessible.role: Accessible.Graphic
    Accessible.name: "Podgląd ustawień na przykładowym zdjęciu"
    Accessible.description: backend.settings.format + ", " + backend.settings.framing
    FontLoader { id: captionFont; source: "../assets/fonts/Anton-Regular.ttf" }
    Timer {
        objectName: "previewCaptionTimer"
        interval: Math.round(420 / root.tempo)
        running: root.visible && root.playing && backend.settings.burn && Theme.motion
        repeat: true
        onTriggered: root.wordIndex = (root.wordIndex + 1) % root.words.length
    }
    function timeRange() {
        if (backend.settings.mode === "Film · minuty") return root.tempo === 1 ? "60 s na część" : "60 s → 54,5 s po eksporcie";
        const a = Number(backend.settings.minimum.replace(",", "."));
        const b = Number(backend.settings.maximum.replace(",", "."));
        if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 0 || b <= 0) return "Ustaw długość klipu";
        const lo = Math.min(40, Math.max(15, Math.min(a, b))) / root.tempo;
        const hi = Math.min(40, Math.max(15, Math.max(a, b))) / root.tempo;
        const value = v => Number(v.toFixed(1)).toLocaleString(Qt.locale("pl_PL"), "f", v % 1 ? 1 : 0);
        return value(lo) + "–" + value(hi) + " s po eksporcie";
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12
        Label { text: "Podgląd ustawień"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold }
        Label { Layout.fillWidth: true; text: "Przykładowy kadr"; color: Theme.muted; font.pixelSize: 12 }
        Item {
            id: stage
            Layout.fillWidth: true
            Layout.preferredHeight: root.vertical ? Math.min(width * 16 / 9, root.height - 340) : width * 9 / 16
            Layout.minimumHeight: root.vertical ? 220 : width * 9 / 16
            Rectangle {
                id: frame
                objectName: "settingsPreviewFrame"
                anchors.centerIn: parent
                width: root.vertical ? Math.min(parent.width, parent.height * 9 / 16) : parent.width
                height: root.vertical ? width * 16 / 9 : width * 9 / 16
                color: "black"
                clip: true
                Item {
                    id: picture
                    objectName: "settingsPreviewPicture"
                    width: root.fitted ? frame.width : frame.height * (1672 / 941)
                    height: width * (941 / 1672)
                    x: root.fitted ? 0 : frame.width / 2 - width * (backend.settings.framing === backend.framingLabels[2] ? root.faceCenter : .5)
                    y: (frame.height - height) / 2
                    transform: Scale { objectName: "previewMirrorTransform"; origin.x: picture.width / 2; xScale: backend.settings.mirror ? -1 : 1 }
                    Behavior on x { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
                    Image {
                        id: photo
                        objectName: "settingsPreviewPhoto"
                        anchors.fill: parent
                        source: "../assets/settings-preview-person.png"
                        fillMode: Image.Stretch
                        visible: false
                    }
                    MultiEffect {
                        objectName: "settingsPreviewEffect"
                        anchors.fill: photo
                        source: photo
                        blurEnabled: true; blur: .06; blurMax: 12
                        autoPaddingEnabled: false
                        contrast: backend.settings.light_color ? .035 : 0
                        brightness: backend.settings.light_color ? .012 : 0
                        saturation: backend.settings.light_color ? .04 : 0
                    }
                }
                Row {
                    id: captions
                    objectName: "settingsPreviewCaptions"
                    visible: backend.settings.burn
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: root.vertical ? (root.fitted ? picture.y + picture.height + Math.min(frame.height * .073, (frame.height - picture.height) / 4) : frame.height * .844) - height / 2 : frame.height * .84 - height / 2
                    spacing: frame.width * .014
                    Repeater {
                        model: root.words
                        Text {
                            required property string modelData
                            required property int index
                            text: modelData
                            font.family: captionFont.name
                            font.pixelSize: frame.width * backend.captionSize / 1080
                            color: index === (Theme.motion && root.playing ? root.wordIndex : 3) ? "#ffd700" : "white"
                            opacity: !Theme.motion || !root.playing || index <= root.wordIndex ? 1 : 0
                            style: Text.Outline; styleColor: "black"
                            Accessible.ignored: true
                        }
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { text: root.vertical ? "9:16" : "16:9"; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            Label { objectName: "previewTempoLabel"; text: root.tempo === 1 ? "1×" : "1,1×"; color: Theme.text; font.pixelSize: 13 }
        }
        Label { objectName: "previewLengthLabel"; Layout.fillWidth: true; text: root.timeRange(); color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
        PrimaryButton {
            objectName: "previewPlaybackButton"
            Layout.fillWidth: true
            text: root.playing ? "Wstrzymaj napisy" : "Odtwórz napisy"
            enabled: backend.settings.burn && Theme.motion
            onClicked: root.playing = !root.playing
        }
        Label { Layout.fillWidth: true; text: backend.settings.burn ? "Anton · " + backend.captionSize + " px\nAktualne słowo na żółto." : "Napisy wyłączone"; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
        Item { Layout.fillHeight: true; Layout.minimumHeight: 4 }
        Label { objectName: "previewTranscriptionInfo"; Layout.fillWidth: true; text: "Transkrypcja: " + backend.settings.whisper + ".\nDokładność zmienia rozpoznawanie mowy."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
    }
}
