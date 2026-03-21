import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';
import { ThreadList } from './thread-list';
import { of, Subject, BehaviorSubject } from 'rxjs';
import { vi } from 'vitest';
import { SharedContextService } from '@polecatworks/mfe-shared';

describe('ThreadList', () => {
  let component: ThreadList;
  let fixture: ComponentFixture<ThreadList>;
  let chatServiceSpy: any;
  let routerSpy: any;
  let routerEventsSpec: Subject<any>; // Declare routerEventsSpec here

  beforeEach(async () => {
    chatServiceSpy = {
      threads$: new BehaviorSubject([]),
      refreshThreads: vi.fn(),
      getThreads: vi.fn()
    };

    // Router events setup
    routerEventsSpec = new Subject<any>();
    routerSpy = {
      navigate: vi.fn(),
      events: routerEventsSpec.asObservable(),
      url: '/chat/1'
    };

    await TestBed.configureTestingModule({
      imports: [ThreadList],
      providers: [
        { provide: ChatService, useValue: chatServiceSpy },
        { provide: Router, useValue: routerSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({ get: (key: string) => null })
          }
        },
        {
          provide: SharedContextService,
          useValue: { context$: of({}) }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ThreadList);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should refresh threads on init', () => {
    expect(chatServiceSpy.refreshThreads).toHaveBeenCalled();
  });

  it('should edit thread and handle delete result', () => {
    const thread: Thread = { thread_id: '1', title: 'Test Thread', color: '#000000', user_id: 'u1' };
    const event = { stopPropagation: vi.fn(), preventDefault: vi.fn() } as any;

    chatServiceSpy.deleteThread = vi.fn().mockReturnValue(of({}));

    // Mock MatDialog
    const mockDialogRef = {
      afterClosed: vi.fn().mockReturnValue(of({ action: 'delete' }))
    };
    component['dialog'] = { open: vi.fn().mockReturnValue(mockDialogRef) } as any;

    component.editThread(event, thread);

    expect(event.stopPropagation).toHaveBeenCalled();
    expect(component['dialog'].open).toHaveBeenCalled();
    expect(chatServiceSpy.deleteThread).toHaveBeenCalledWith(thread.thread_id);
    expect(chatServiceSpy.refreshThreads).toHaveBeenCalled();
  });

  it('should edit thread and handle save result', () => {
    const thread: Thread = { thread_id: '1', title: 'Test Thread', color: '#000000', user_id: 'u1' };
    const event = { stopPropagation: vi.fn(), preventDefault: vi.fn() } as any;

    chatServiceSpy.updateThread = vi.fn().mockReturnValue(of({}));

    // Mock MatDialog
    const mockDialogRef = {
      afterClosed: vi.fn().mockReturnValue(of({
        action: 'save',
        data: { title: 'New Title', color: '#ffffff' }
      }))
    };
    component['dialog'] = { open: vi.fn().mockReturnValue(mockDialogRef) } as any;

    component.editThread(event, thread);

    expect(event.stopPropagation).toHaveBeenCalled();
    expect(component['dialog'].open).toHaveBeenCalled();
    expect(chatServiceSpy.updateThread).toHaveBeenCalledWith(thread.thread_id, { title: 'New Title', color: '#ffffff' });
    expect(chatServiceSpy.refreshThreads).toHaveBeenCalled();
  });
});
