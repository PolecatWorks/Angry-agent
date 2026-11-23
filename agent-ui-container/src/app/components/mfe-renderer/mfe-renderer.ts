import {
  Component,
  Input,
  Output,
  EventEmitter,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnChanges,
  SimpleChanges,
  OnDestroy
} from '@angular/core';
import { loadRemoteModule } from '@angular-architects/native-federation';
import {
  ChatService,
  MfeCanvasController,
  JsonPatchOp,
  AiFieldAttribution,
  CanvasSelection
} from '../../services/chat.service';

@Component({
  selector: 'app-mfe-renderer',
  standalone: true,
  template: '<div #container></div>',
})
export class MfeRenderer implements AfterViewInit, OnChanges, OnDestroy {
  @Input() mfe: string = '';
  @Input() component: string = '';
  @Input() content: any;
  @Input() data: any; // Keep for backward compatibility
  @Input() attributions: AiFieldAttribution[] = [];
  @Input() title: string = '';
  @Input() name: string = '';
  @Input() description: string = '';
  @Input() id: string | null = null;

  @Output() action = new EventEmitter<{ action: string; payload: any }>();
  @Output() stateChange = new EventEmitter<{ state: any; patches: JsonPatchOp[] }>();
  @Output() selectionChange = new EventEmitter<CanvasSelection | null>();

  @ViewChild('container', { static: true }) container!: ElementRef;

  private controller?: MfeCanvasController;
  private isMounted = false;
  private lastMountedKey = '';

  /** Optional loader override for deterministic unit testing */
  remoteLoader: (options: { remoteName: string; exposedModule: string }) => Promise<any> =
    (options) => loadRemoteModule(options);

  constructor(private chatService: ChatService) {}

  async ngAfterViewInit() {
    await this.mountRemote();
  }

  async ngOnChanges(changes: SimpleChanges) {
    if (!this.isMounted) {
      return;
    }

    const mfeChanged = changes['mfe'] && !changes['mfe'].firstChange;
    const componentChanged = changes['component'] && !changes['component'].firstChange;

    if (mfeChanged || componentChanged) {
      this.cleanupController();
      await this.mountRemote();
      return;
    }

    const contentChanged = changes['content'] && !changes['content'].firstChange;
    const dataChanged = changes['data'] && !changes['data'].firstChange;
    const attributionsChanged = changes['attributions'] && !changes['attributions'].firstChange;

    if ((contentChanged || dataChanged || attributionsChanged) && this.controller) {
      const nextPayload = this.content !== undefined ? this.content : this.data;
      this.controller.applyPatch(nextPayload, this.attributions || []);
    }
  }

  private async mountRemote() {
    if (!this.mfe || !this.component) return;

    const exposedModule = this.component.startsWith('./') ? this.component : `./${this.component}`;
    this.lastMountedKey = `${this.mfe}:${exposedModule}`;

    try {
      const m = await this.remoteLoader({
        remoteName: this.mfe,
        exposedModule: exposedModule
      });

      if (m && m.mount) {
        const props = {
          content: this.content,
          initialState: this.content,
          data: this.data || this.content,
          id: this.id,
          title: this.title,
          name: this.name,
          description: this.description,
          onAction: (actionStr: string, payload: any) => {
            this.action.emit({ action: actionStr, payload });
          },
          onStateChange: (state: any, patches: JsonPatchOp[] = []) => {
            this.stateChange.emit({ state, patches });
          },
          onSelectionChange: (selection: CanvasSelection | null) => {
            if (selection) {
              this.selectionChange.emit({
                ...selection,
                canvasId: this.id || selection.canvasId || 'inline-mfe'
              });
            } else {
              this.selectionChange.emit(null);
            }
          }
        };

        const mountResult = await m.mount(this.container.nativeElement, props);
        this.controller = this.normalizeController(mountResult);
        this.isMounted = true;

        if (this.id && this.chatService) {
          this.chatService.registerCanvasController(this.id, this.controller);
        }
      } else {
        throw new Error(`Remote module ${this.mfe}/${exposedModule} does not export mount function.`);
      }
    } catch (err) {
      console.error(`Failed to load ${exposedModule} from ${this.mfe}`, err);
      this.container.nativeElement.innerHTML = `
        <div style="color: #ff4d4d; padding: 10px; border: 1px solid #ff4d4d; border-radius: 4px; font-family: monospace; font-size: 12px; background: rgba(255, 77, 77, 0.1);">
          Error loading MFE ${this.mfe}: ${exposedModule}
        </div>
      `;
    }
  }

  private normalizeController(mountResult: any): MfeCanvasController {
    if (mountResult && typeof mountResult.applyPatch === 'function') {
      return {
        applyPatch: (patches, attributions) => mountResult.applyPatch(patches, attributions),
        getState: () => (typeof mountResult.getState === 'function' ? mountResult.getState() : this.content),
        getSchema: () => (typeof mountResult.getSchema === 'function' ? mountResult.getSchema() : {}),
        unmount: () => {
          if (typeof mountResult.unmount === 'function') {
            mountResult.unmount();
          } else if (typeof mountResult === 'function') {
            mountResult();
          }
        }
      };
    }

    // Legacy MFE fallback where mount() returns a plain () => void unmount function
    let fallbackState = this.content ?? this.data ?? {};
    return {
      applyPatch: (patches) => {
        fallbackState = patches;
      },
      getState: () => fallbackState,
      getSchema: () => ({}),
      unmount: () => {
        if (typeof mountResult === 'function') {
          mountResult();
        }
      }
    };
  }

  private cleanupController() {
    if (this.id && this.chatService) {
      this.chatService.unregisterCanvasController(this.id);
    }
    if (this.controller) {
      this.controller.unmount();
      this.controller = undefined;
    }
    this.isMounted = false;
  }

  ngOnDestroy() {
    this.cleanupController();
  }
}
