import QtQuick
import QtQuick.Controls
Switch {
    id: control
    implicitHeight: 34
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45
    font.pixelSize: 13
    indicator: Rectangle {
        implicitWidth: 38; implicitHeight: 22
        y: (control.height - height) / 2
        radius: 11
        color: control.checked ? Theme.accent : control.hovered ? Theme.hover : Theme.border
        border.color: control.visualFocus ? Theme.focus : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Rectangle { width: 16; height: 16; radius: 8; y: 3; x: control.checked ? 19 : 3; color: "white"; Behavior on x { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } } }
    }
    contentItem: Text { text: control.text; font: control.font; color: Theme.text; leftPadding: 50; verticalAlignment: Text.AlignVCenter }
}
