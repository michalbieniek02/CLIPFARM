import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
Item {
    id: root
    required property var clipData
    required property int index
    property bool editing: false
    property bool revealed: !backend.animationsEnabled
    implicitHeight: content.implicitHeight + 36
    HoverHandler { id: hover }
    opacity: revealed ? 1 : 0
    transform: Translate { y: root.revealed ? (hover.hovered && backend.animationsEnabled ? -2 : 0) : 12; Behavior on y { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } } }
    Behavior on opacity { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
    Timer { interval: Math.min(root.index, 6) * 45 + 10; running: !root.revealed; onTriggered: root.revealed = true }
    Rectangle { anchors.fill: parent; radius: Theme.radius; color: hover.hovered ? Theme.raised : Theme.surface; border.color: hover.hovered ? "#486174" : Theme.border; layer.enabled: true; layer.effect: MultiEffect { shadowEnabled: true; shadowColor: "#28000000"; shadowBlur: 0.2; shadowVerticalOffset: 3 } Behavior on color { ColorAnimation { duration: Theme.fast } } Behavior on border.color { ColorAnimation { duration: Theme.fast } } }
    RowLayout {
        id: content
        anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.margins: 18; spacing: 18
        CheckBox { checked: root.clipData.selected !== false; enabled: !backend.busy; Accessible.name: "Zaznacz klip " + root.clipData.title; onToggled: backend.selectClip(root.index, checked); palette.highlight: Theme.accent; palette.windowText: Theme.text }
        Image { Layout.preferredWidth: 116; Layout.preferredHeight: 80; source: root.clipData.thumbnail || "../assets/clipfarm-mark.png"; fillMode: Image.PreserveAspectFit; asynchronous: true }
        ColumnLayout {
            Layout.fillWidth: true; spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Label { Layout.fillWidth: true; text: root.clipData.title || "Klip " + (root.index + 1); color: Theme.text; font.pixelSize: 16; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
                Rectangle { visible: Number(root.clipData.score) > 0; implicitWidth: 62; implicitHeight: 27; radius: 7; color: "#154034"; Label { anchors.centerIn: parent; text: root.clipData.score + "/" + (Number(root.clipData.score) <= 10 ? "10" : "100"); color: "#b8eaa4"; font.pixelSize: 12; font.weight: Font.DemiBold } }
            }
            Label { Layout.fillWidth: true; visible: !!root.clipData.reason; text: root.clipData.reason || ""; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Label { Layout.fillWidth: true; visible: !root.editing; text: Number(root.clipData.start).toFixed(1) + " – " + Number(root.clipData.end).toFixed(1) + " s  ·  " + (root.clipData.end - root.clipData.start).toFixed(1) + " s"; color: Theme.muted; font.pixelSize: 11 }
                Field { id: start; visible: root.editing; Layout.preferredWidth: 74; text: Number(root.clipData.start).toFixed(2); Accessible.name: "Początek klipu w sekundach" }
                Field { id: end; visible: root.editing; Layout.preferredWidth: 74; text: Number(root.clipData.end).toFixed(2); Accessible.name: "Koniec klipu w sekundach" }
                PrimaryButton { visible: root.editing; text: "Zapisz"; implicitHeight: 32; enabled: !backend.busy; onClicked: { backend.editClip(root.index, start.text, end.text); root.editing = false; } }
                Item { visible: root.editing; Layout.fillWidth: true }
                PrimaryButton { text: "Podgląd"; implicitHeight: 32; enabled: !backend.busy; onClicked: backend.previewClip(root.index) }
                PrimaryButton { text: root.editing ? "Anuluj" : "Edytuj"; implicitHeight: 32; enabled: !backend.busy; onClicked: root.editing = !root.editing }
                PrimaryButton { text: "Usuń"; implicitHeight: 32; destructive: true; enabled: !backend.busy; onClicked: backend.removeClip(root.index) }
            }
        }
    }
}
