import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { RouterOutlet } from '@angular/router';
import { ThreadList } from '../thread-list/thread-list';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, MatSidenavModule, RouterOutlet, ThreadList],
  templateUrl: './main-layout.html',
  styleUrls: ['./main-layout.scss']
})
export class MainLayout {
}
