# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'frm_principal.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QSizePolicy, QSpacerItem,
    QStackedWidget, QVBoxLayout, QWidget)

class Ui_frmPrincipal(object):
    def setupUi(self, frmPrincipal):
        if not frmPrincipal.objectName():
            frmPrincipal.setObjectName(u"frmPrincipal")
        frmPrincipal.setMinimumSize(QSize(960, 600))
        self.qwdCentral = QWidget(frmPrincipal)
        self.qwdCentral.setObjectName(u"qwdCentral")
        self.layoutRaiz = QHBoxLayout(self.qwdCentral)
        self.layoutRaiz.setSpacing(0)
        self.layoutRaiz.setObjectName(u"layoutRaiz")
        self.layoutRaiz.setContentsMargins(0, 0, 0, 0)
        self.qfrmSidebar = QFrame(self.qwdCentral)
        self.qfrmSidebar.setObjectName(u"qfrmSidebar")
        self.qfrmSidebar.setMinimumSize(QSize(220, 0))
        self.qfrmSidebar.setMaximumSize(QSize(220, 16777215))
        self.layoutSidebar = QVBoxLayout(self.qfrmSidebar)
        self.layoutSidebar.setSpacing(12)
        self.layoutSidebar.setObjectName(u"layoutSidebar")
        self.layoutSidebar.setContentsMargins(12, 16, 12, 16)
        self.qlblTitulo = QLabel(self.qfrmSidebar)
        self.qlblTitulo.setObjectName(u"qlblTitulo")
        self.qlblTitulo.setAlignment(Qt.AlignCenter)

        self.layoutSidebar.addWidget(self.qlblTitulo)

        self.qfrmModulos = QFrame(self.qfrmSidebar)
        self.qfrmModulos.setObjectName(u"qfrmModulos")
        self.layoutModulos = QVBoxLayout(self.qfrmModulos)
        self.layoutModulos.setSpacing(8)
        self.layoutModulos.setObjectName(u"layoutModulos")
        self.layoutModulos.setContentsMargins(0, 0, 0, 0)

        self.layoutSidebar.addWidget(self.qfrmModulos)

        self.spacerSidebar = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.layoutSidebar.addItem(self.spacerSidebar)

        self.qbtnTema = QPushButton(self.qfrmSidebar)
        self.qbtnTema.setObjectName(u"qbtnTema")
        icon = QIcon()
        icon.addFile(u":/TemaClaroOscuro256.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.qbtnTema.setIcon(icon)
        self.qbtnTema.setIconSize(QSize(24, 24))

        self.layoutSidebar.addWidget(self.qbtnTema)

        self.qbtnSalir = QPushButton(self.qfrmSidebar)
        self.qbtnSalir.setObjectName(u"qbtnSalir")
        icon1 = QIcon()
        icon1.addFile(u":/Apagado64.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.qbtnSalir.setIcon(icon1)
        self.qbtnSalir.setIconSize(QSize(24, 24))

        self.layoutSidebar.addWidget(self.qbtnSalir)


        self.layoutRaiz.addWidget(self.qfrmSidebar)

        self.qfrmContenido = QFrame(self.qwdCentral)
        self.qfrmContenido.setObjectName(u"qfrmContenido")
        self.layoutContenido = QVBoxLayout(self.qfrmContenido)
        self.layoutContenido.setObjectName(u"layoutContenido")
        self.layoutContenido.setContentsMargins(16, 16, 16, 16)
        self.qstwPaginas = QStackedWidget(self.qfrmContenido)
        self.qstwPaginas.setObjectName(u"qstwPaginas")
        self.qwdInicio = QWidget()
        self.qwdInicio.setObjectName(u"qwdInicio")
        self.layoutInicio = QVBoxLayout(self.qwdInicio)
        self.layoutInicio.setObjectName(u"layoutInicio")
        self.qlblBienvenida = QLabel(self.qwdInicio)
        self.qlblBienvenida.setObjectName(u"qlblBienvenida")
        self.qlblBienvenida.setAlignment(Qt.AlignCenter)

        self.layoutInicio.addWidget(self.qlblBienvenida)

        self.qstwPaginas.addWidget(self.qwdInicio)

        self.layoutContenido.addWidget(self.qstwPaginas)


        self.layoutRaiz.addWidget(self.qfrmContenido)

        frmPrincipal.setCentralWidget(self.qwdCentral)

        self.retranslateUi(frmPrincipal)

        self.qstwPaginas.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(frmPrincipal)
    # setupUi

    def retranslateUi(self, frmPrincipal):
        frmPrincipal.setWindowTitle(QCoreApplication.translate("frmPrincipal", u"ControlLaboral", None))
        self.qlblTitulo.setText(QCoreApplication.translate("frmPrincipal", u"ControlLaboral", None))
        self.qbtnTema.setText(QCoreApplication.translate("frmPrincipal", u"Tema claro/oscuro", None))
#if QT_CONFIG(tooltip)
        self.qbtnTema.setToolTip(QCoreApplication.translate("frmPrincipal", u"Alternar entre tema claro y oscuro", None))
#endif // QT_CONFIG(tooltip)
        self.qbtnSalir.setText(QCoreApplication.translate("frmPrincipal", u"Salir", None))
#if QT_CONFIG(tooltip)
        self.qbtnSalir.setToolTip(QCoreApplication.translate("frmPrincipal", u"Cerrar la aplicaci\u00f3n", None))
#endif // QT_CONFIG(tooltip)
        self.qbtnSalir.setProperty(u"tipo", QCoreApplication.translate("frmPrincipal", u"peligro", None))
        self.qlblBienvenida.setText(QCoreApplication.translate("frmPrincipal", u"Bienvenido a ControlLaboral", None))
    # retranslateUi

