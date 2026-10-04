import QtQuick
import QtQuick.Controls
ComboBox {
    id: control
    implicitHeight: 40
    font.pixelSize: 13
    leftPadding: 12; rightPadding: 30
    opacity: enabled ? 1 : 0.45
    contentItem: Text { text: control.displayText; font: control.font; color: Theme.text; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
    indicator: Text { x: control.width - 25; y: 10; text: "⌄"; color: Theme.muted; font.pixelSize: 18 }
    background: Rectangle { radius: Theme.controlRadius; color: control.hovered ? Theme.hover : Theme.raised; border.color: control.visualFocus ? Theme.focus : Theme.border; border.width: control.visualFocus ? 2 : 1; Behavior on color { ColorAnimation { duration: Theme.fast } } }
    delegate: ItemDelegate {
        required property var modelData
        required property int index
        width: control.width; height: 38
        contentItem: Text { text: modelData; color: Theme.text; font: control.font; verticalAlignment: Text.AlignVCenter }
        highlighted: control.highlightedIndex === index
        background: Rectangle { color: highlighted ? Theme.hover : Theme.surface; radius: 6 }
    }
    popup: Popup {
        y: control.height + 6; width: control.width; padding: 6
        implicitHeight: Math.min(contentItem.implicitHeight + 12, 240)
        contentItem: ListView { clip: true; implicitHeight: contentHeight; model: control.popup.visible ? control.delegateModel : null; currentIndex: control.highlightedIndex }
        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: 10 }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast } }
        exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.fast } }
    }
}
