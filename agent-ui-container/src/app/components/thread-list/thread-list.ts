import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule, Router } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-thread-list',
  standalone: true,
  imports: [CommonModule, MatListModule, MatButtonModule, MatIconModule, RouterModule],
  templateUrl: './thread-list.html',
  styleUrls: ['./thread-list.scss']
})
export class ThreadList implements OnInit {
  threads$: Observable<Thread[]>;

  constructor(private chatService: ChatService, private router: Router) {
    this.threads$ = this.chatService.threads$;
  }

  ngOnInit() {
    this.chatService.refreshThreads();
  }

  newChat() {
    this.router.navigate(['/chat']);
  }
}
