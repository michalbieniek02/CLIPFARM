import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "." as Components

Item {
    implicitHeight: 44
    PrimaryButton {
        id: action
        objectName: "installUpdateButton"
        anchors.centerIn: parent
        implicitWidth: 44
        visible: !updates.installing
        enabled: !backend.busy
        primary: true
        text: ""
        Accessible.name: "Pobierz aktualizację i uruchom aplikację ponownie"
        ToolTip.visible: hovered
        ToolTip.text: updates.status + "\nPobierz aktualizację i uruchom ponownie."
        ToolTip.delay: 350
        onClicked: backend.installUpdate()
        contentItem: Item {
            Canvas {
                anchors.centerIn: parent
                width: 22; height: 22
                onPaint: {
                    const ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);
                    ctx.strokeStyle = Theme.text;
                    ctx.lineWidth = 2; ctx.lineCap = "round"; ctx.lineJoin = "round";
                    ctx.beginPath();
                    ctx.moveTo(11, 15); ctx.lineTo(11, 4);
                    ctx.moveTo(6, 9); ctx.lineTo(11, 4); ctx.lineTo(16, 9);
                    ctx.moveTo(4, 15); ctx.lineTo(4, 19); ctx.lineTo(18, 19); ctx.lineTo(18, 15);
                    ctx.stroke();
                }
            }
            Rectangle { anchors.right: parent.right; anchors.top: parent.top; width: 6; height: 6; radius: 3; color: Theme.green }
        }
    }
    ColumnLayout {
        anchors.fill: parent
        visible: updates.installing
        spacing: 5
        Label { objectName: "updateDownloadInfo"; Layout.fillWidth: true; text: updates.status; color: Theme.text; font.pixelSize: 11; wrapMode: Text.WordWrap }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Components.ProgressBar { objectName: "updateProgressBar"; Layout.fillWidth: true; value: updates.progress; busy: true }
            Label { text: Math.round(updates.progress * 100) + "%"; color: Theme.muted; font.pixelSize: 11 }
        }
    }
}
