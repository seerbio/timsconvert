import os
import re
from timsconvert.data_input import dot_d_detection
from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale, QMetaObject, QObject, QPoint, QRect, QSize,
                            QTime, QUrl, Qt, QTimer, QProcess)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor, QFont, QFontDatabase, QGradient, QIcon, QImage,
                           QKeySequence, QLinearGradient, QPainter, QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QLabel, QLineEdit, QListView, QMainWindow, QPushButton,
                               QRadioButton, QSizePolicy, QSpinBox, QWidget, QFileDialog, QProgressBar, QDialog,
                               QDialogButtonBox)
from timsconvert_gui_template import Ui_TimsconvertGuiWindow

# TODO: add comments
class TimsconvertGuiWindow(QMainWindow, Ui_TimsconvertGuiWindow):
    def __init__(self):
        super(TimsconvertGuiWindow, self).__init__()

        self.args = {'input': None,  # QLineEdit + QPushButton (select directory dialogue button)
                     'outdir': '',  # QLineEdit + QPushButton (select directory dialogue button)
                     'mode': 'centroid',  # QRadioButton
                     'compression': 'zlib',  # QCheckbox
                     'ms2_only': False,  # QCheckbox
                     'use_raw_calibration': False,  # QCheckbox
                     'pressure_compensation_strategy': 'none',  # QRadioButton
                     'exclude_mobility': False,  # QCheckbox
                     'encoding': 64,  # QRadioButton
                     'barebones_metadata': False,  # QCheckbox
                     'profile_bins': 0,  # QLineEdit
                     'maldi_output_file': 'combined',  # QRadioButton
                     'maldi_plate_map': '',  # QLineEdit + QPushButton (select file dialogue button)
                     'imzml_mode': 'processed',  # QRadioButton
                     'verbose': False}  # QCheckbox

        self.selected_row_from_queue = ''
        self.errors = None

        self.setupUi(self)

        # Show/Hide Binning Settings if Profile Mode
        self.ModeProfileRadio.clicked.connect(self.show_hide_binning)
        self.ModeCentroidRadio.clicked.connect(self.show_hide_binning)
        self.ModeRawRadio.clicked.connect(self.show_hide_binning)

        # File browser dialogues
        # Add Input
        self.AddInputDialogueButton.clicked.connect(self.browse_input)
        # Select Output Directory
        self.OutputDirectoryBrowseButton.clicked.connect(self.select_output_directory)
        # Select MALDI Plate Map
        self.MaldiPlateMapBrowseButton.clicked.connect(self.select_maldi_plate_map)

        # Queue
        # Select Input
        self.InputList.selectionModel().selectionChanged.connect(self.select_from_queue)
        # Remove Input
        self.RemoveFromQueueButton.clicked.connect(self.remove_from_queue)

        # Initialize Process
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.stateChanged.connect(self.handle_state)
        self.process.finished.connect(self.process_finished)

        # Run
        self.RunButton.clicked.connect(self.run)

    def show_hide_binning(self):
        if self.ModeProfileRadio.isChecked():
            self.NumBinsLabel.setVisible(True)
            self.BinSpectraCheckbox.setVisible(True)
            self.NumBinsSpinBox.setVisible(True)
        else:
            self.NumBinsLabel.setVisible(False)
            self.BinSpectraCheckbox.setVisible(False)
            self.NumBinsSpinBox.setVisible(False)

    def browse_input(self):
        self.args['input'] = QFileDialog().getExistingDirectory(self, 'Select Directory...', '')
        if os.path.isdir(self.args['input']):
            if not self.args['input'].endswith('.d'):
                input_filenames = dot_d_detection(self.args['input'])
            elif self.args['input'].endswith('.d'):
                input_filenames = [self.args['input']]
            if self.args['input'] is not None:
                input_filenames = [i.replace('/', '\\') for i in input_filenames]
                input_filenames = [os.path.split(i)[-1] for i in input_filenames]
                self.populate_table(input_filenames)

    def select_output_directory(self):
        self.args['outdir'] = QFileDialog().getExistingDirectory(self, 'Select Directory...', '').replace('/', '\\')
        self.OutputDirectoryLine.setText(self.args['outdir'])

    def select_maldi_plate_map(self):
        self.args['maldi_plate_map'] = QFileDialog().getOpenFileName(self,
                                                                     'Select MALDI Plate Map...',
                                                                     '',
                                                                     filter='Comma Separated Values (*.csv)')
        self.args['maldi_plate_map'] = self.args['maldi_plate_map'][0].replace('/', '\\')
        self.MaldiPlateMapLine.setText(self.args['maldi_plate_map'])

    def select_from_queue(self):
        self.selected_row_from_queue = self.InputList.selectionModel().selectedIndexes()

    def remove_from_queue(self):
        for row in sorted([i.row() for i in self.selected_row_from_queue], reverse=True):
            self.InputList.removeRow(row)

    def run(self):
        self.AddInputDialogueButton.setEnabled(False)
        self.RemoveFromQueueButton.setEnabled(False)
        self.OutputDirectoryBrowseButton.setEnabled(False)
        self.MaldiPlateMapBrowseButton.setEnabled(False)
        self.RunButton.setEnabled(False)

        # Collect arguments from GUI.
        self.args['outdir'] = str(self.OutputDirectoryLine.text())
        if (self.ModeProfileRadio.isChecked() and
                not self.ModeCentroidRadio.isChecked() and
                not self.ModeRawRadio.isChecked()):
            self.args['mode'] = 'profile'
        elif (not self.ModeProfileRadio.isChecked() and
              self.ModeCentroidRadio.isChecked() and
              not self.ModeRawRadio.isChecked()):
            self.args['mode'] = 'centroid'
        elif (not self.ModeProfileRadio.isChecked() and
              not self.ModeCentroidRadio.isChecked() and
              self.ModeRawRadio.isChecked()):
            self.args['mode'] = 'raw'
        if self.CompressionCheckbox.isChecked():
            self.args['compression'] = 'zlib'
        else:
            self.args['compression'] = 'none'
        if self.Ms2OnlyCheckbox.isChecked():
            self.args['ms2_only'] = True
        else:
            self.args['ms2_only'] = False
        if self.RecalibratedDataCheckbox.isChecked():
            self.args['use_raw_calibration'] = False
        else:
            self.args['use_raw_calibration'] = True
        if (self.MobilityCompensationNoneRadio.isChecked() and
                not self.MobilityCompensationGlobalRadio.isChecked() and
                not self.MobilityCompensationFrameRadio.isChecked()):
            self.args['pressure_compensation_strategy'] = 'none'
        elif (not self.MobilityCompensationNoneRadio.isChecked() and
              self.MobilityCompensationGlobalRadio.isChecked() and
              not self.MobilityCompensationFrameRadio.isChecked()):
            self.args['pressure_compensation_strategy'] = 'global'
        elif (not self.MobilityCompensationNoneRadio.isChecked() and
              not self.MobilityCompensationGlobalRadio.isChecked() and
              self.MobilityCompensationFrameRadio.isChecked()):
            self.args['pressure_compensation_strategy'] = 'frame'
        if self.ExcludeMobilityCheckbox.isChecked():
            self.args['exclude_mobility'] = True
        else:
            self.args['exclude_mobility'] = False
        if self.Encoding64Radio.isChecked() and not self.Encoding32Radio.isChecked():
            self.args['encoding'] = 64
        elif not self.Encoding64Radio.isChecked() and self.Encoding32Radio.isChecked():
            self.args['encoding'] = 32
        if self.BarebonesMetadataCheckbox.isChecked():
            self.args['barebones_metadata'] = True
        else:
            self.args['barebones_metadata'] = False
        if self.BinSpectraCheckbox.isChecked():
            self.args['profile_bins'] = int(self.NumBinsSpinBox.text())
        else:
            self.args['profile_bins'] = 0
        if (self.MaldiOutputFileCombinedRadio.isChecked() and
                not self.MaldiOutputFileIndividualRadio.isChecked() and
                not self.MaldiOutputFileSampleRadio.isChecked()):
            self.args['maldi_output_file'] = 'combined'
        elif (not self.MaldiOutputFileCombinedRadio.isChecked() and
              self.MaldiOutputFileIndividualRadio.isChecked() and
              not self.MaldiOutputFileSampleRadio.isChecked()):
            self.args['maldi_output_file'] = 'individual'
        elif (not self.MaldiOutputFileCombinedRadio.isChecked() and
              not self.MaldiOutputFileIndividualRadio.isChecked() and
              self.MaldiOutputFileSampleRadio.isChecked()):
            self.args['maldi_output_file'] = 'sample'
        self.args['maldi_plate_map'] = str(self.MaldiPlateMapLine.text())
        if self.MaldiImzmlModeProcessedRadio.isChecked() and not self.MaldiImzmlModeContinuousRadio.isChecked():
            self.args['imzml_mode'] = 'processed'
        elif not self.MaldiImzmlModeProcessedRadio.isChecked() and self.MaldiImzmlModeContinuousRadio.isChecked():
            self.args['imzml_mode'] = 'continuous'

        # Convert Data
        if self.args['input'] is not None:
            # Build and run command in QProcess.
            process_args = ['run.py']
            for key, value in self.args.items():
                if key not in ['ms2_only', 'use_raw_calibration', 'exclude_mobility', 'barebones_metadata', 'verbose']:
                    process_args.append(f'--{key}')
                    process_args.append(str(value))
                elif self.args[key]:
                    process_args.append(f'--{key}')
            self.process.start('python', process_args)

            # Replace queue list with progress bars.
            for row in range(self.InputList.rowCount()):
                progress_bar = QProgressBar()
                progress_bar.setValue(0)
                progress_bar.setFormat(f"{self.InputList.item(row, 0).text()}")
                progress_bar.setObjectName(f"{self.InputList.item(row, 0).text()}")
                progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.InputList.setCellWidget(row, 0, progress_bar)
        else:
            # TODO: change this to a popup box that says no files in queue
            print('No input files found.')

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode('utf8')
        percentage = re.search(r'(\d+)%', stdout)
        dot_d_file = re.search(r'([^:/]+\.d)', stdout)
        if percentage and dot_d_file:
            percentage = int(percentage.group(1))
            dot_d_file = dot_d_file.group(1).split('\\')[-1]
            self.InputList.findChild(QProgressBar, dot_d_file).setValue(percentage)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode('utf8')
        self.errors += stderr + '\n'

    def process_finished(self):
        # TODO: popup box saying finished
        # TODO: clear queue table widget when acknowledged
        # TODO: text to show any errors that appeared in finished box popup
        self.AddInputDialogueButton.setEnabled(True)
        self.RemoveFromQueueButton.setEnabled(True)
        self.OutputDirectoryBrowseButton.setEnabled(True)
        self.MaldiPlateMapBrowseButton.setEnabled(True)
        self.RunButton.setEnabled(True)


class EmptyQueueDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('TIMSCONVERT - Error')
        self.ButtonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)


if __name__ == '__main__':
    app = QApplication([])

    window = TimsconvertGuiWindow()
    window.show()

    app.exec()
