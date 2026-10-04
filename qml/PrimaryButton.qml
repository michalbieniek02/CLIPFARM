import QtQuick
import QtQuick.Controls
Button {
    id: control
    property bool primary: false
    property bool destructive: false
    implicitHeight: 40
    implicitWidth: Math.max(80, label.implicitWidth + 28)
    hoverEnabled: true
    opacity: enabled ? 1 : 0.42
    scale: down && Theme.fast > 0 ? 0.97 : 1
    font.pixelSize: 13
    font.weight: Font.DemiBold
    Accessible.name: text
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
    Behavior on opacity { NumberAnimation { duration: Theme.fast } }
    contentItem: Text { id: label; text: control.text; font: control.font; color: control.destructive ? Theme.danger : Theme.text; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
    background: Rectangle {
        radius: Theme.controlRadius
        color: control.primary ? (control.down ? "#005dbd" : control.hovered ? Theme.accentHover : Theme.accent) : (control.down ? Theme.raised : control.hovered ? Theme.hover : Theme.surface)
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? Theme.focus : control.primary ? "transparent" : Theme.border
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Behavior on border.color { ColorAnimation { duration: Theme.fast } }
    }
}
