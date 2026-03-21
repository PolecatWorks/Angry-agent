import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ChatService, Thread } from '../../services/chat.service';
import { AudioService } from '../../services/audio.service';
import { Observable } from 'rxjs';
import { SharedContextService } from 'mfe-shared';
import { EditThreadDialog, EditThreadDialogData } from '../edit-thread-dialog/edit-thread-dialog';

@Component({
  selector: 'app-thread-list',
  standalone: true,
  imports: [CommonModule, MatListModule, MatButtonModule, MatIconModule, RouterModule, MatDialogModule],
  templateUrl: './thread-list.html',
  styleUrls: ['./thread-list.scss']
})
export class ThreadList implements OnInit {
  threads$: Observable<Thread[]>;

  constructor(
    private chatService: ChatService,
    public audioService: AudioService,
    public sharedContext: SharedContextService,
    private router: Router,
    private route: ActivatedRoute,
    private dialog: MatDialog
  ) {
    this.threads$ = this.chatService.threads$;
    this.sharedContext.context$.subscribe((user: any) => {
      console.log('User:', user);
    });
  }

  ngOnInit() {
    this.sharedContext.context$.subscribe((user: any) => {
      console.log('Shared Context User:', user);
    });
    this.chatService.refreshThreads();
  }

  newChat() {
    this.audioService.playNewChat();
    this.router.navigate(['chat'], { relativeTo: this.route });
  }

  editThread(event: Event, thread: Thread) {
    event.stopPropagation();
    event.preventDefault();

    const dialogRef = this.dialog.open(EditThreadDialog, {
      width: '400px',
      data: {
        title: thread.title,
        color: thread.color
      } as EditThreadDialogData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result) return;

      if (result.action === 'delete') {
        this.chatService.deleteThread(thread.thread_id).subscribe({
          next: () => {
            this.chatService.refreshThreads();
            if (this.router.url.includes(thread.thread_id)) {
              this.router.navigate(['chat'], { relativeTo: this.route });
            }
          },
          error: (err) => console.error('Error deleting thread', err)
        });
      } else if (result.action === 'save') {
        // We PUT the entire resource state required for the update
        const updatedThread = {
          title: result.data.title || '',
          color: result.data.color || ''
        };

        // We can always perform the update since PUT implies replacing state
        // and the user explicitly clicked "Save".
        this.chatService.updateThread(thread.thread_id, updatedThread).subscribe({
          next: () => {
            this.chatService.refreshThreads();
          },
          error: (err) => console.error('Error updating thread', err)
        });
      }
    });
  }
}
