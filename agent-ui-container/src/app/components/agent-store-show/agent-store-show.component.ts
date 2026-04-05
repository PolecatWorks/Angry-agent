import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-agent-store-show',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './agent-store-show.component.html',
  styleUrls: ['./agent-store-show.component.scss']
})
export class AgentStoreShowComponent {
  @Input() data: any;
}
