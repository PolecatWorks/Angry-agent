import { Component, Input, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { loadRemoteModule } from '@angular-architects/native-federation';

@Component({
  selector: 'app-mermaid-renderer',
  standalone: true,
  template: '<div #container></div>',
})
export class MermaidRenderer implements AfterViewInit, OnDestroy {
  @Input() content: string = '';
  @ViewChild('container', { static: true }) container!: ElementRef;

  private unmountFn?: () => void;

  async ngAfterViewInit() {
    if (!this.content) return;
    
    try {
      // Load the MermaidShowWrapper from mfe1
      const m = await loadRemoteModule({
        remoteName: 'mfe1',
        exposedModule: './MermaidShowWrapper'
      });

      if (m && m.mount) {
        this.unmountFn = await m.mount(this.container.nativeElement, { content: this.content });
      }
    } catch (err) {
      console.error('Failed to load MermaidShowWrapper from mfe1', err);
      this.container.nativeElement.innerHTML = `
        <div style="color: #ff4d4d; padding: 10px; border: 1px solid #ff4d4d; border-radius: 4px; font-family: monospace; font-size: 12px; background: rgba(255, 77, 77, 0.1);">
          Error loading Mermaid component from mfe1
        </div>
      `;
    }
  }

  ngOnDestroy() {
    if (this.unmountFn) {
      this.unmountFn();
    }
  }
}
