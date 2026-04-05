import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { ChatService, UserSettings } from '../../services/chat.service';

@Component({
    selector: 'app-settings',
    standalone: true,
    imports: [CommonModule, FormsModule, MatSlideToggleModule],
    templateUrl: './settings.html'
})
export class SettingsComponent implements OnInit {
    settings: UserSettings = { learning_mode_enabled: false };
    loading = true;
    saving = false;

    constructor(private chatService: ChatService) {}

    ngOnInit() {
        this.chatService.getUserSettings().subscribe({
            next: (res) => {
                this.settings = res;
                this.loading = false;
            },
            error: (err) => {
                console.error('Failed to load settings', err);
                this.loading = false;
            }
        });
    }

    onSettingsChange() {
        this.saving = true;
        this.chatService.updateUserSettings(this.settings).subscribe({
            next: () => {
                this.saving = false;
            },
            error: (err) => {
                console.error('Failed to save settings', err);
                this.saving = false;
                // Revert state if failed
                this.settings.learning_mode_enabled = !this.settings.learning_mode_enabled;
            }
        });
    }
}
