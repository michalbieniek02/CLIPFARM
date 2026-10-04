import QtQuick
import QtQuick.Controls

Choice {
    id: control
    font.family: currentText
    font.pixelSize: 17
    delegate: ItemDelegate {
        required property var modelData
        required property int index
        objectName: "captionFontOption" + index
        width: control.width
        height: 44
        contentItem: Text {
            text: modelData
            font.family: modelData
            font.pixelSize: 18
            color: Theme.text
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        highlighted: control.highlightedIndex === index
        background: Rectangle { color: highlighted ? Theme.hover : Theme.surface; radius: 6 }
        Accessible.name: modelData
    }
}
