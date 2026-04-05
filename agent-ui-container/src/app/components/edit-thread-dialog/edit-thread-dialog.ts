import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

export interface EditThreadDialogData {
  title: string;
  color: string;
  learning_mode_enabled?: boolean;
}

@Component({
  selector: 'app-edit-thread-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    FormsModule,
    MatDialogModule,
    MatSlideToggleModule
  ],
  templateUrl: './edit-thread-dialog.html',
  styleUrls: ['./edit-thread-dialog.scss']
})
export class EditThreadDialog {
  colors = [
    { name: 'Default Blue', value: '#3f51b5' },
    { name: 'Green', value: '#4caf50' },
    { name: 'Purple', value: '#9c27b0' },
    { name: 'Orange', value: '#ff9800' },
    { name: 'Teal', value: '#009688' },
    { name: 'Red', value: '#f44336' },
  ];

  title: string;
  selectedColor: string;
  learningModeEnabled: boolean;
  showDeleteConfirm = false;

  constructor(
    public dialogRef: MatDialogRef<EditThreadDialog>,
    @Inject(MAT_DIALOG_DATA) public data: EditThreadDialogData,
  ) {
    this.title = data.title || '';
    this.selectedColor = data.color || '';
    this.learningModeEnabled = data.learning_mode_enabled || false;
  }

  onNoClick(): void {
    this.dialogRef.close();
  }

  onSaveClick(): void {
    this.dialogRef.close({
      action: 'save',
      data: {
        title: this.title,
        color: this.selectedColor,
        learning_mode_enabled: this.learningModeEnabled,
      }
    });
  }

  onDeleteClick(): void {
    this.showDeleteConfirm = true;
  }

  cancelDelete(): void {
    this.showDeleteConfirm = false;
  }

  confirmDelete(): void {
    this.dialogRef.close({
      action: 'delete'
    });
  }

  selectColor(colorValue: string): void {
    this.selectedColor = colorValue;
  }
}
