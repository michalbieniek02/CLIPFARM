import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Rectangle {
    id: root
    objectName: "settingsPreview"
    color: Theme.surface
    radius: Theme.radius
    readonly property bool vertical: backend.settings.format !== "Oryginalny"
    readonly property bool phoneFormat: backend.settings.format === "Telefon 9:19,5"
    readonly property bool fitted: vertical && backend.settings.framing === "Cały obraz · czarne pasy"
    readonly property bool movable: vertical && backend.settings.framing !== "Podążaj za twarzą"
    readonly property real tempo: backend.settings.speed_up ? 1.1 : 1
    readonly property var layout: backend.previewLayout
    property bool playing: true
    property int wordIndex: 3
    readonly property var words: ["TAK", "WYGLĄDA", "TWÓJ", "KLIP"]
    Accessible.role: Accessible.Graphic
    Accessible.name: "Podgląd ustawień na przykładowym zdjęciu w telefonie"
    Accessible.description: "Przeciągnij napisy lub obraz, aby zmienić ich położenie. Wypełnij ekran ustawia format i kadrowanie także w eksporcie."

    function clamp(value, low, high) { return Math.min(high, Math.max(low, value)); }
    function captionPosition(x, y) {
        if (backend.busy) return;
        backend.setSetting("caption_x", root.clamp(x, captions.width / frame.width / 2, 1 - captions.width / frame.width / 2));
        backend.setSetting("caption_y", root.clamp(y, captions.height / frame.height / 2, 1 - captions.height / frame.height / 2));
        backend.setSetting("caption_custom", true);
    }
    function focusPosition(x, y) {
        if (backend.busy || !root.movable) return;
        backend.setSetting("fit_x", root.clamp(x, 0, 1));
        backend.setSetting("fit_y", root.clamp(y, 0, 1));
    }
    function nudgeFocus(x, y) {
        root.focusPosition((frame.width / 2 - picture.x) / picture.width + x,
                           (frame.height / 2 - picture.y) / picture.height + y);
    }
    function resetPosition() {
        backend.setSetting("caption_custom", false);
        backend.setSetting("caption_x", .5);
        backend.setSetting("caption_y", .844);
        backend.setSetting("fit_zoom", 1);
        backend.setSetting("fit_x", .5);
        backend.setSetting("fit_y", .5);
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
    Timer {
        objectName: "previewCaptionTimer"
        interval: Math.round(420 / root.tempo)
        running: root.visible && root.playing && backend.settings.burn && Theme.motion
        repeat: true
        onTriggered: root.wordIndex = (root.wordIndex + 1) % root.words.length
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10
        Label { text: "Podgląd ustawień"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold }
        Label { Layout.fillWidth: true; text: "Przykładowy kadr"; color: Theme.muted; font.pixelSize: 12 }
        Item {
            id: stage
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(width * 19.5 / 9, root.height - 354)
            Layout.minimumHeight: 280
            Item {
                id: phone
                objectName: "settingsPreviewPhone"
                anchors.centerIn: parent
                width: Math.min(parent.width - 6, (parent.height - 12) * 9 / 19.5 + 12)
                height: (width - 12) * 19.5 / 9 + 12
                Rectangle { x: -2; y: phone.height * .20; width: 3; height: phone.height * .075; radius: 1.5; color: "#64666a" }
                Rectangle { x: -2; y: phone.height * .30; width: 3; height: phone.height * .075; radius: 1.5; color: "#64666a" }
                Rectangle { x: phone.width - 1; y: phone.height * .28; width: 3; height: phone.height * .11; radius: 1.5; color: "#64666a" }
                Rectangle { anchors.fill: parent; radius: phone.width * .17; color: "#a3a5a8" }
                Rectangle { anchors.fill: parent; anchors.margins: 2; radius: phone.width * .16; color: "#141518" }
                Rectangle {
                    id: screen
                    objectName: "settingsPreviewScreen"
                    anchors.fill: parent
                    anchors.margins: 6
                    radius: phone.width * .135
                    color: "black"
                    clip: true
                    layer.enabled: true
                    layer.effect: MultiEffect { maskEnabled: true; maskSource: screenMask; autoPaddingEnabled: false }
                    Rectangle {
                        id: frame
                        objectName: "settingsPreviewFrame"
                        anchors.centerIn: parent
                        width: parent.width
                        height: width * root.layout.canvas_height / root.layout.canvas_width
                        color: "black"
                        clip: true
                        readonly property real canvasScale: width / root.layout.canvas_width
                        Item {
                            id: picture
                            objectName: "settingsPreviewPicture"
                            width: root.layout.image_width * frame.canvasScale
                            height: root.layout.image_height * frame.canvasScale
                            x: root.layout.image_x * frame.canvasScale
                            y: root.layout.image_y * frame.canvasScale
                            transform: Scale { objectName: "previewMirrorTransform"; origin.x: picture.width / 2; xScale: backend.settings.mirror ? -1 : 1 }
                            Image { id: photo; objectName: "settingsPreviewPhoto"; anchors.fill: parent; source: "../assets/settings-preview-person.png"; fillMode: Image.Stretch; visible: false }
                            MultiEffect {
                                objectName: "settingsPreviewEffect"
                                anchors.fill: photo
                                source: photo
                                blurEnabled: true; blur: .06; blurMax: 12; autoPaddingEnabled: false
                                contrast: backend.settings.light_color ? .035 : 0
                                brightness: backend.settings.light_color ? .012 : 0
                                saturation: backend.settings.light_color ? .04 : 0
                            }
                        }
                        MouseArea {
                            id: imageDrag
                            objectName: "settingsPreviewImageDrag"
                            anchors.fill: parent
                            enabled: root.movable && !backend.busy
                            hoverEnabled: true
                            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                            property real initialX
                            property real initialY
                            property real focusX
                            property real focusY
                            onPressed: mouse => {
                                imageFocus.forceActiveFocus();
                                initialX = mouse.x; initialY = mouse.y;
                                focusX = (frame.width / 2 - picture.x) / picture.width;
                                focusY = (frame.height / 2 - picture.y) / picture.height;
                            }
                            onPositionChanged: mouse => {
                                if (pressed) root.focusPosition(focusX - (mouse.x - initialX) / picture.width, focusY - (mouse.y - initialY) / picture.height);
                            }
                            onWheel: wheel => {
                                backend.setSetting("fit_zoom", root.clamp(backend.settings.fit_zoom + (wheel.angleDelta.y > 0 ? .1 : -.1), 1, 4));
                                wheel.accepted = true;
                            }
                        }
                        Item {
                            id: imageFocus
                            anchors.fill: parent
                            activeFocusOnTab: root.movable && !backend.busy
                            enabled: root.movable && !backend.busy
                            Accessible.role: Accessible.Graphic
                            Accessible.name: "Położenie kadru"
                            Accessible.description: "Przesuwaj strzałkami. Przybliżenie zmienisz suwakiem w lewym panelu."
                            Keys.onLeftPressed: event => { root.nudgeFocus(.01, 0); event.accepted = true; }
                            Keys.onRightPressed: event => { root.nudgeFocus(-.01, 0); event.accepted = true; }
                            Keys.onUpPressed: event => { root.nudgeFocus(0, .01); event.accepted = true; }
                            Keys.onDownPressed: event => { root.nudgeFocus(0, -.01); event.accepted = true; }
                            Rectangle { anchors.fill: parent; color: "transparent"; border.color: Theme.focus; border.width: 2; visible: imageFocus.activeFocus }
                        }
                        Row {
                            id: captions
                            objectName: "settingsPreviewCaptions"
                            visible: backend.settings.burn
                            x: root.clamp(root.layout.caption_x * frame.canvasScale - width / 2, 0, Math.max(0, frame.width - width))
                            y: root.clamp(root.layout.caption_y * frame.canvasScale - height / 2, 0, Math.max(0, frame.height - height))
                            spacing: frame.width * .014
                            readonly property real captionScale: frame.width / 1080
                            readonly property real fittedSize: Math.min(backend.captionSize * captionScale, (frame.width - 12 - spacing * 3) / Math.max(1, captionMetrics.width) * backend.captionSize * captionScale)
                            TextMetrics { id: captionMetrics; font.family: backend.captionFont; font.pixelSize: backend.captionSize * captions.captionScale; text: root.words.join("") }
                            Repeater {
                                model: root.words
                                Text {
                                    required property string modelData
                                    required property int index
                                    text: modelData
                                    font.family: backend.captionFont
                                    font.pixelSize: captions.fittedSize
                                    color: index === (Theme.motion && root.playing ? root.wordIndex : 3) ? "#ffd700" : "white"
                                    opacity: !Theme.motion || !root.playing || index <= root.wordIndex ? 1 : 0
                                    style: Text.Outline; styleColor: "black"
                                    Accessible.ignored: true
                                }
                            }
                        }
                        Item {
                            id: captionFocus
                            objectName: "settingsPreviewCaptionDrag"
                            x: Math.max(0, captions.x - 5)
                            y: Math.max(0, captions.y - 6)
                            width: Math.min(frame.width - x, captions.width + 10)
                            height: Math.max(28, captions.height + 12)
                            visible: captions.visible
                            enabled: !backend.busy
                            activeFocusOnTab: true
                            Accessible.role: Accessible.Graphic
                            Accessible.name: "Położenie napisów"
                            Accessible.description: "Przeciągnij lub przesuwaj strzałkami. Pozycję można też wpisać w procentach w lewym panelu."
                            function moveBy(x, y) { root.captionPosition((captions.x + captions.width / 2) / frame.width + x, (captions.y + captions.height / 2) / frame.height + y); }
                            Keys.onLeftPressed: event => { moveBy(-.01, 0); event.accepted = true; }
                            Keys.onRightPressed: event => { moveBy(.01, 0); event.accepted = true; }
                            Keys.onUpPressed: event => { moveBy(0, -.01); event.accepted = true; }
                            Keys.onDownPressed: event => { moveBy(0, .01); event.accepted = true; }
                            Rectangle { anchors.fill: parent; radius: 4; color: "transparent"; border.color: Theme.focus; border.width: 1; visible: captionPointer.containsMouse || captionPointer.pressed || captionFocus.activeFocus }
                            MouseArea {
                                id: captionPointer
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                                property point initialPoint
                                property real initialX
                                property real initialY
                                onPressed: mouse => {
                                    captionFocus.forceActiveFocus();
                                    initialPoint = mapToItem(frame, mouse.x, mouse.y);
                                    initialX = (captions.x + captions.width / 2) / frame.width;
                                    initialY = (captions.y + captions.height / 2) / frame.height;
                                }
                                onPositionChanged: mouse => {
                                    if (pressed) {
                                        const p = mapToItem(frame, mouse.x, mouse.y);
                                        root.captionPosition(initialX + (p.x - initialPoint.x) / frame.width, initialY + (p.y - initialPoint.y) / frame.height);
                                    }
                                }
                            }
                        }
                    }
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 7; width: parent.width * .30; height: phone.width * .077; radius: height / 2; color: "#050506"; Rectangle { width: parent.height * .4; height: width; radius: width / 2; x: parent.width - width - 5; anchors.verticalCenter: parent.verticalCenter; color: "#111b2c" } }
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 5; width: parent.width * .34; height: 2; radius: 1; color: "#d2d2d2"; opacity: .8 }
                }
                Rectangle { id: screenMask; objectName: "settingsPreviewScreenMask"; anchors.fill: screen; radius: screen.radius; color: "white"; layer.enabled: true; visible: false }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { text: root.phoneFormat ? "9:19,5" : root.vertical ? "9:16" : "16:9"; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            PrimaryButton { objectName: "previewFillScreenButton"; implicitHeight: 32; font.pixelSize: 11; text: "Wypełnij ekran"; enabled: !backend.busy && !(root.phoneFormat && backend.settings.framing === "Wypełnij · środek"); Accessible.description: "Eksport 1080 na 2340 pikseli. Przytnie obraz, aby wypełnić ekran telefonu w podglądzie."; onClicked: backend.fillPhoneScreen() }
            Label { objectName: "previewTempoLabel"; text: root.tempo === 1 ? "1×" : "1,1×"; color: Theme.text; font.pixelSize: 13 }
        }
        Label { Layout.fillWidth: true; text: root.movable ? "Przeciągnij obraz lub napisy.\nKółko myszy: przybliżenie." : "Przeciągnij napisy na kadrze.\nStrzałki: precyzyjne przesuwanie."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
        RowLayout {
            Layout.fillWidth: true
            PrimaryButton { objectName: "previewPlaybackButton"; Layout.fillWidth: true; implicitHeight: 34; font.pixelSize: 11; text: root.playing ? "Wstrzymaj" : "Odtwórz"; enabled: backend.settings.burn && Theme.motion; onClicked: root.playing = !root.playing }
            PrimaryButton { objectName: "previewResetButton"; Layout.fillWidth: true; implicitHeight: 34; font.pixelSize: 11; text: "Reset pozycji"; enabled: !backend.busy; onClicked: root.resetPosition() }
        }
        Label { objectName: "previewLengthLabel"; Layout.fillWidth: true; text: root.timeRange(); color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
        Label { Layout.fillWidth: true; text: backend.settings.burn ? backend.captionFont + " · " + backend.captionSize + " px\nAktualne słowo na żółto." : "Napisy wyłączone"; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
        Item { Layout.fillHeight: true; Layout.minimumHeight: 0 }
        Label { objectName: "previewTranscriptionInfo"; Layout.fillWidth: true; text: "Transkrypcja: " + backend.settings.whisper + ".\nDokładność zmienia rozpoznawanie mowy."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
    }
}
