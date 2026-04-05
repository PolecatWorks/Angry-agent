import { ApplicationRef, createComponent, EnvironmentInjector, Type } from '@angular/core';
import { createApplication } from '@angular/platform-browser';
import { AgentStoreShowComponent } from './agent-store-show.component';

const appRefs = new Map<HTMLElement, ApplicationRef>();
const componentRefs = new Map<HTMLElement, any>();

export async function mount(container: HTMLElement, props: any) {
  if (appRefs.has(container)) {
    console.warn('Angular app already mounted on this container, unmounting first.');
    unmount(container);
  }

  // Create an Angular application instance (without bootstrapping a root component yet)
  const appRef = await createApplication();

  // Create the component instance and attach it to the provided DOM element
  const environmentInjector = appRef.injector.get(EnvironmentInjector);
  const componentRef = createComponent(AgentStoreShowComponent as Type<any>, {
    environmentInjector,
    hostElement: container,
  });

  // Set the inputs
  if (props) {
    if (props.content) {
      componentRef.setInput('data', props.content);
    } else if (props.data) {
      componentRef.setInput('data', props.data);
    }
  }

  // Attach the component view to the ApplicationRef so it participates in change detection
  appRef.attachView(componentRef.hostView);

  // Trigger immediate change detection for this component
  componentRef.changeDetectorRef.detectChanges();

  // Store references for cleanup
  appRefs.set(container, appRef);
  componentRefs.set(container, componentRef);

  return () => unmount(container);
}

export function unmount(container: HTMLElement) {
  const componentRef = componentRefs.get(container);
  if (componentRef) {
    componentRef.destroy();
    componentRefs.delete(container);
  }

  const appRef = appRefs.get(container);
  if (appRef) {
    appRef.destroy();
    appRefs.delete(container);
  }
}
