import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
Rectangle {
    id: root
    property bool opened: false
    property real reveal: opened ? 1 : 0
    objectName: "previewPanel"
    enabled: opened
    visible: reveal > 0
    function focusFirst() { closeButton.forceActiveFocus() }
    width: Math.min(parent.width - 48, 680); height: parent.height - 48
    x: parent.width + 8 - reveal * (width + 32)
    y: 24; z: 20; radius: Theme.radius; color: Theme.surface
    Behavior on reveal { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
    onOpenedChanged: { if (!opened) player.stop(); else focusFirst(); }
    MediaPlayer {
        id: player; objectName: "previewPlayer"
        source: backend.previewUrl
        audioOutput: AudioOutput { volume: volume.value }
        videoOutput: video
        onSourceChanged: { if (source.toString().length > 0) player.play() }
        onErrorOccurred: (error, text) => backend.reportError("Podgląd wideo: " + text)
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 14
        RowLayout { Layout.fillWidth: true; Label { text: "Podgląd klipu"; color: Theme.text; font.pixelSize: 22; Layout.fillWidth: true } PrimaryButton { id: closeButton; objectName: "previewClose"; text: "Zamknij"; KeyNavigation.tab: seek; KeyNavigation.backtab: volume; onClicked: { root.opened = false; backend.closePreview(); } } }
        Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "black"; radius: 10; VideoOutput { id: video; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit } }
        Slider { id: seek; objectName: "previewSeek"; KeyNavigation.tab: play; KeyNavigation.backtab: closeButton; Layout.fillWidth: true; from: 0; to: player.duration; value: player.position; onMoved: player.setPosition(value) }
        RowLayout {
            Layout.fillWidth: true
            PrimaryButton { id: play; objectName: "previewPlay"; KeyNavigation.tab: volume; KeyNavigation.backtab: seek; primary: true; text: player.playbackState === MediaPlayer.PlayingState ? "Pauza" : "Odtwórz"; onClicked: player.playbackState === MediaPlayer.PlayingState ? player.pause() : player.play() }
            Label { text: Math.floor(player.position/1000) + " / " + Math.floor(player.duration/1000) + " s"; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
            Label { text: "Głośność"; color: Theme.muted; font.pixelSize: 11 }
            Slider { id: volume; objectName: "previewVolume"; KeyNavigation.tab: closeButton; KeyNavigation.backtab: play; Layout.preferredWidth: 110; from: 0; to: 1; value: 0.8 }
        }
    }
    Connections { target: backend; function onPreviewReady() { root.opened = true } }
}
