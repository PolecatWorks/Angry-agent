import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule, Router } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';

@Component({
  selector: 'app-thread-list',
  standalone: true,
  imports: [CommonModule, MatListModule, MatButtonModule, MatIconModule, RouterModule],
  templateUrl: './thread-list.html',
  styleUrls: ['./thread-list.scss']
})
export class ThreadList implements OnInit {
  threads: Thread[] = [];

  constructor(private chatService: ChatService, private router: Router) {}

  ngOnInit() {
    this.loadThreads();
  }

  loadThreads() {
    this.chatService.getThreads().subscribe({
        next: (res) => {
            this.threads = res.threads;
        },
        error: (err) => console.error(err)
    });
  }

  newChat() {
    this.router.navigate(['/chat']);
  }
}
