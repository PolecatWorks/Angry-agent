import { Component, Input, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { loadRemoteModule } from '@angular-architects/native-federation';

@Component({
  selector: 'app-mfe-renderer',
  standalone: true,
  template: '<div #container></div>',
})
export class MfeRenderer implements AfterViewInit, OnDestroy {
  @Input() mfe: string = '';
  @Input() component: string = '';
  @Input() content: any;
  @Input() data: any; // Keep for backward compatibility

  @ViewChild('container', { static: true }) container! : ElementRef;

  private unmountFn?: () => void;

  async ngAfterViewInit() {
    if (!this.mfe || !this.component) return;
    
    try {
      const m = await loadRemoteModule({
        remoteName: this.mfe,
        exposedModule: this.component
      });

      if (m && m.mount) {
        // Pass the content directly as props
        const props = this.content || { content: this.data };
        this.unmountFn = await m.mount(this.container.nativeElement, props);
      } else {
        throw new Error(`Remote module ${this.mfe}/${this.component} does not export mount function.`);
      }
    } catch (err) {
      console.error(`Failed to load ${this.component} from ${this.mfe}`, err);
      this.container.nativeElement.innerHTML = `
        <div style="color: #ff4d4d; padding: 10px; border: 1px solid #ff4d4d; border-radius: 4px; font-family: monospace; font-size: 12px; background: rgba(255, 77, 77, 0.1);">
          Error loading MFE ${this.mfe}: ${this.component}
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
