import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Rectangle {
    id: root
    property bool opened: false
    property real reveal: opened ? 1 : 0
    objectName: "detailsPanel"
    enabled: opened
    visible: reveal > 0
    function focusFirst() { closeButton.forceActiveFocus() }
    signal closeRequested()
    width: Math.min(520, parent.width - 48); height: parent.height
    x: parent.width + 8 - reveal * (width + 8)
    color: Theme.sidebar; z: 30
    Behavior on reveal { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 24; spacing: 18
        RowLayout { Layout.fillWidth: true; Label { text: "Szczegóły zadania"; color: Theme.text; font.pixelSize: 22; Layout.fillWidth: true } PrimaryButton { id: closeButton; objectName: "detailsClose"; text: "Zamknij"; KeyNavigation.tab: logText; KeyNavigation.backtab: logText; onClicked: root.closeRequested() } }
        Label { Layout.fillWidth: true; text: backend.errorMessage ? "Wystąpił błąd. Poniżej znajdziesz pełny log, który możesz zaznaczyć i skopiować." : "Pełny log przetwarzania filmu."; color: Theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            TextArea { id: logText; objectName: "detailsLog"; activeFocusOnTab: true; Keys.onTabPressed: closeButton.forceActiveFocus(); Keys.onBacktabPressed: closeButton.forceActiveFocus(); text: backend.logs || "Brak komunikatów."; readOnly: true; selectByMouse: true; wrapMode: Text.Wrap; color: Theme.text; font.family: "Consolas"; font.pixelSize: 12; padding: 14; background: Rectangle { color: Theme.background; radius: 10 } }
        }
    }
}
