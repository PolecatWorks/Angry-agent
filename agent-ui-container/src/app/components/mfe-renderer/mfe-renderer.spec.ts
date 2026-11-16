import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SimpleChange } from '@angular/core';
import { MfeRenderer } from './mfe-renderer';
import { ChatService, MfeCanvasController } from '../../services/chat.service';
import { vi } from 'vitest';

describe('MfeRenderer (Shared Canvas MfeCanvasController)', () => {
  let component: MfeRenderer;
  let fixture: ComponentFixture<MfeRenderer>;
  let chatServiceSpy: any;

  beforeEach(async () => {
    chatServiceSpy = {
      registerCanvasController: vi.fn(),
      unregisterCanvasController: vi.fn()
    };

    await TestBed.configureTestingModule({
      imports: [MfeRenderer],
      providers: [{ provide: ChatService, useValue: chatServiceSpy }]
    }).compileComponents();

    fixture = TestBed.createComponent(MfeRenderer);
    component = fixture.componentInstance;
  });

  it('should mount an MFE returning MfeCanvasController and apply patches in-place on ngOnChanges without unmounting', async () => {
    const applyPatchSpy = vi.fn();
    const unmountSpy = vi.fn();
    let mountedProps: any;

    const mockController: MfeCanvasController = {
      applyPatch: applyPatchSpy,
      getState: () => ({ firstName: 'Grace' }),
      getSchema: () => ({ type: 'object' }),
      unmount: unmountSpy
    };

    component.remoteLoader = vi.fn().mockResolvedValue({
      mount: vi.fn().mockImplementation(async (_el: HTMLElement, props: any) => {
        mountedProps = props;
        return mockController;
      })
    });

    component.id = 'viz-123';
    component.mfe = 'mfe1';
    component.component = './PersonalDataFormWrapper';
    component.content = { firstName: 'John' };

    await component.ngAfterViewInit();

    expect(chatServiceSpy.registerCanvasController).toHaveBeenCalledWith('viz-123', expect.anything());
    expect(unmountSpy).not.toHaveBeenCalled();

    // Update content via ngOnChanges -> should call applyPatch in place, NOT unmount!
    const nextContent = { firstName: 'Grace', email: 'grace@navy.mil' };
    component.content = nextContent;
    component.attributions = [{ path: '/firstName', source: 'ai', confidence: 0.99 }];

    await component.ngOnChanges({
      content: new SimpleChange({ firstName: 'John', email: 'john@navy.mil' }, nextContent, false),
      attributions: new SimpleChange([], component.attributions, false)
    });

    expect(applyPatchSpy).toHaveBeenCalledWith(nextContent, component.attributions);
    expect(unmountSpy).not.toHaveBeenCalled();

    // Verify onStateChange and onSelectionChange callbacks forward to @Output emitters
    const stateEvents: any[] = [];
    const selectionEvents: any[] = [];
    component.stateChange.subscribe((e) => stateEvents.push(e));
    component.selectionChange.subscribe((s) => selectionEvents.push(s));

    mountedProps.onStateChange({ firstName: 'Ada' }, [{ op: 'replace', path: '/firstName', value: 'Ada' }]);
    mountedProps.onSelectionChange({ canvasId: 'viz-123', path: '/firstName', label: 'First Name' });

    expect(stateEvents).toEqual([
      { state: { firstName: 'Ada' }, patches: [{ op: 'replace', path: '/firstName', value: 'Ada' }] }
    ]);
    expect(selectionEvents).toEqual([
      { canvasId: 'viz-123', path: '/firstName', label: 'First Name' }
    ]);

    // Unmount on destroy
    component.ngOnDestroy();
    expect(chatServiceSpy.unregisterCanvasController).toHaveBeenCalledWith('viz-123');
    expect(unmountSpy).toHaveBeenCalledTimes(1);
  });

  it('should support legacy MFE wrappers that return a plain unmount function', async () => {
    const legacyUnmountSpy = vi.fn();
    component.remoteLoader = vi.fn().mockResolvedValue({
      mount: vi.fn().mockResolvedValue(legacyUnmountSpy)
    });

    component.id = 'viz-legacy';
    component.mfe = 'mfe1';
    component.component = './LegacyWrapper';
    component.content = { hello: 'world' };

    await component.ngAfterViewInit();
    expect(chatServiceSpy.registerCanvasController).toHaveBeenCalledWith('viz-legacy', expect.anything());

    component.ngOnDestroy();
    expect(legacyUnmountSpy).toHaveBeenCalledTimes(1);
  });
});
