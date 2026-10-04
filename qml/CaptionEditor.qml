import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    objectName: "captionEditor"
    property bool opened: false
    property real reveal: opened ? 1 : 0
    property var drafts: ({})
    property string editorStatus: ""
    property bool saveFailed: false
    signal closeRequested()
    enabled: opened
    visible: reveal > 0
    width: Math.min(540, parent.width - 48)
    height: parent.height
    x: parent.width + 8 - reveal * (width + 8)
    color: Theme.sidebar
    z: 30
    Behavior on reveal { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }

    function focusFirst() { closeButton.forceActiveFocus() }
    function formatTime(value) {
        var seconds = Math.max(0, Math.floor(Number(value) || 0))
        var hours = Math.floor(seconds / 3600)
        var minutes = Math.floor(seconds / 60) % 60
        var rest = seconds % 60
        return (hours ? hours + ":" : "")
                + (minutes < 10 ? "0" : "") + minutes + ":"
                + (rest < 10 ? "0" : "") + rest
    }
    function draftFor(index, original) {
        return drafts[index] !== undefined ? drafts[index] : original
    }
    function saveRow(index, text) {
        if (backend.busy)
            return
        if (backend.editCaption(index, text)) {
            var remaining = Object.assign({}, drafts)
            delete remaining[index]
            drafts = remaining
            saveFailed = false
            editorStatus = "Zapisano fragment. Sprawdź napisy w podglądzie."
            focusRow(index, false)
        } else {
            saveFailed = true
            editorStatus = "Nie udało się zapisać fragmentu. Sprawdź tekst i spróbuj ponownie."
        }
    }
    function focusRow(index, save) {
        if (backend.busy || index < 0 || index >= rows.count) {
            closeButton.forceActiveFocus()
            return
        }
        rows.positionViewAtIndex(index, ListView.Contain)
        rows.forceLayout()
        Qt.callLater(function() {
            var row = rows.itemAtIndex(index)
            if (row)
                row.focusControl(save)
            else
                closeButton.forceActiveFocus()
        })
    }
    onOpenedChanged: {
        if (!opened) {
            drafts = ({})
            editorStatus = ""
            saveFailed = false
        }
    }
    Keys.onEscapePressed: closeRequested()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "Edytuj napisy"
                color: Theme.text
                font.pixelSize: 22
                Layout.fillWidth: true
            }
            PrimaryButton {
                id: closeButton
                objectName: "captionEditorClose"
                text: "Zamknij"
                onClicked: root.closeRequested()
                Keys.onTabPressed: root.focusRow(0, false)
                Keys.onBacktabPressed: root.focusRow(rows.count - 1, true)
            }
        }
        Label {
            Layout.fillWidth: true
            text: "Popraw tekst i zapisz wybrany fragment. Czasy początku i końca pozostają bez zmian."
            color: Theme.muted
            font.pixelSize: 13
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            visible: root.editorStatus !== ""
            text: root.editorStatus
            color: root.saveFailed ? Theme.danger : Theme.muted
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            Accessible.role: Accessible.StaticText
        }
        ListView {
            id: rows
            objectName: "captionEditorRows"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 12
            model: root.opened ? backend.captionRows : []
            ScrollBar.vertical: ScrollBar { }
            delegate: Rectangle {
                id: row
                required property int index
                required property var modelData
                width: rows.width - 12
                height: content.implicitHeight + 28
                color: Theme.background
                radius: 10
                border.width: 1
                border.color: Theme.border
                function focusControl(save) {
                    if (save && saveButton.enabled)
                        saveButton.forceActiveFocus()
                    else
                        captionText.forceActiveFocus()
                }
                ColumnLayout {
                    id: content
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 14
                    spacing: 10
                    Label {
                        text: root.formatTime(row.modelData.start) + " – "
                              + root.formatTime(row.modelData.end)
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                    TextArea {
                        id: captionText
                        objectName: "captionText_" + row.index
                        Layout.fillWidth: true
                        implicitHeight: Math.max(84, contentHeight + topPadding + bottomPadding)
                        enabled: !backend.busy
                        text: root.draftFor(row.index, row.modelData.text)
                        color: Theme.text
                        selectionColor: Theme.accent
                        selectedTextColor: "white"
                        wrapMode: TextEdit.Wrap
                        selectByMouse: true
                        activeFocusOnTab: true
                        font.pixelSize: 14
                        padding: 12
                        Accessible.name: "Tekst napisów od " + root.formatTime(row.modelData.start)
                        onTextChanged: {
                            if (root.opened) {
                                if (text === row.modelData.text)
                                    delete root.drafts[row.index]
                                else
                                    root.drafts[row.index] = text
                            }
                        }
                        Keys.onTabPressed: {
                            if (saveButton.enabled)
                                saveButton.forceActiveFocus()
                            else
                                root.focusRow(row.index + 1, false)
                        }
                        Keys.onBacktabPressed: root.focusRow(row.index - 1, true)
                        Keys.onEscapePressed: root.closeRequested()
                        Keys.onReturnPressed: function(event) {
                            if (event.modifiers & Qt.ControlModifier) {
                                root.saveRow(row.index, text)
                                event.accepted = true
                            } else {
                                event.accepted = false
                            }
                        }
                        background: Rectangle {
                            color: Theme.raised
                            radius: Theme.controlRadius
                            border.width: captionText.activeFocus ? 2 : 1
                            border.color: captionText.activeFocus ? Theme.focus : Theme.border
                        }
                    }
                    PrimaryButton {
                        id: saveButton
                        objectName: "captionSave_" + row.index
                        text: "Zapisz fragment"
                        primary: true
                        enabled: !backend.busy && captionText.text !== row.modelData.text
                        Layout.alignment: Qt.AlignRight
                        onClicked: root.saveRow(row.index, captionText.text)
                        Keys.onTabPressed: root.focusRow(row.index + 1, false)
                        Keys.onBacktabPressed: captionText.forceActiveFocus()
                        Keys.onEscapePressed: root.closeRequested()
                    }
                }
            }
            Label {
                anchors.centerIn: parent
                width: parent.width - 24
                visible: rows.count === 0
                text: "Najpierw dodaj film i przygotuj transkrypcję."
                color: Theme.muted
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}
