import QtQuick
Image {
    source: "../assets/clipfarm-mark.png"
    // Display the supplied mark without its unused transparent side margins.
    sourceClipRect: Qt.rect(250, 0, 625, 748)
    fillMode: Image.PreserveAspectFit
}
