import QtQuick
import QtQuick.Controls
Rectangle {
    id: root
    property var options: []
    property string value: ""
    property real selectedPosition: Math.max(0, options.indexOf(value))
    Behavior on selectedPosition { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
    signal chosen(string value)
    implicitHeight: 40
    color: Theme.raised; radius: Theme.controlRadius
    Rectangle { x: 4 + root.selectedPosition * width; y: 4; width: (root.width - 8) / Math.max(1, root.options.length); height: root.height - 8; radius: 6; color: Theme.accent }
    Row {
        anchors.fill: parent; anchors.margins: 4
        Repeater {
            model: root.options
            Button {
                required property string modelData
                width: (root.width - 8) / root.options.length; height: root.height - 8
                hoverEnabled: true
                contentItem: Text { text: modelData; color: root.value === modelData ? "white" : Theme.muted; font.pixelSize: 12; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; Behavior on color { ColorAnimation { duration: Theme.fast } } }
                background: Rectangle { color: hovered && root.value !== modelData ? Theme.hover : "transparent"; radius: 6; border.color: visualFocus ? Theme.focus : "transparent" }
                onClicked: root.chosen(modelData)
            }
        }
    }
}
