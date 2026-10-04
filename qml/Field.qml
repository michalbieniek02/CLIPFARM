import QtQuick
import QtQuick.Controls
TextField {
    id: control
    implicitHeight: 38
    color: Theme.text
    selectionColor: Theme.accent
    selectedTextColor: "white"
    placeholderTextColor: Theme.muted
    font.pixelSize: 13
    padding: 12
    opacity: enabled ? 1 : 0.45
    background: Rectangle { radius: Theme.controlRadius; color: Theme.raised; border.width: control.activeFocus ? 2 : 1; border.color: control.activeFocus ? Theme.focus : Theme.border; Behavior on border.color { ColorAnimation { duration: Theme.fast } } }
}
