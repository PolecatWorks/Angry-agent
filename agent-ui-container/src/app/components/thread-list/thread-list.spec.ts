import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, NavigationEnd } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ChatService, Thread } from '../../services/chat.service';
import { ThreadList } from './thread-list';
import { of, Subject } from 'rxjs';
import { vi } from 'vitest';

describe('ThreadList', () => {
  let component: ThreadList;
  let fixture: ComponentFixture<ThreadList>;
  let chatServiceSpy: any;
  let routerSpy: any;
  let routerEventsSpec: Subject<any>;

  beforeEach(async () => {
    chatServiceSpy = {
      getThreads: vi.fn(),
      threadCreated$: new Subject<void>()
    };

    // Router events setup
    routerEventsSpec = new Subject<any>();
    routerSpy = {
      navigate: vi.fn(),
      events: routerEventsSpec.asObservable()
    };

    chatServiceSpy.getThreads.mockReturnValue(of({ threads: [] }));

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
        // Also mock AuthService if needed, though this component primarily uses ChatService
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

  it('should load threads on init', () => {
    const mockThreads: Thread[] = [
      { thread_id: '1', user_id: 'u1', title: 'T1' }
    ];
    chatServiceSpy.getThreads.mockReturnValue(of({ threads: mockThreads }));

    // Manually call loadThreads since ngOnInit ran with empty list
    component.loadThreads();
    expect(chatServiceSpy.getThreads).toHaveBeenCalled();
    expect(component.threads).toEqual(mockThreads);
  });

  it('should reload threads on NavigationEnd', () => {
    const mockThreads: Thread[] = [
      { thread_id: '2', user_id: 'u1', title: 'T2' }
    ];
    chatServiceSpy.getThreads.mockReturnValue(of({ threads: mockThreads }));

    routerEventsSpec.next(new NavigationEnd(1, '/chat', '/chat'));

    expect(chatServiceSpy.getThreads).toHaveBeenCalledTimes(2); // Once on init, once on nav
    expect(component.threads).toEqual(mockThreads);
  });

  it('should navigate to new chat', () => {
    component.newChat();
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/chat']);
  });
});
