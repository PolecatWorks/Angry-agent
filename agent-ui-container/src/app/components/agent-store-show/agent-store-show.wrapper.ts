import { createApplication } from '@angular/platform-browser';
import { AgentStoreShowComponent } from './agent-store-show.component';

export async function mount(element: HTMLElement, props: any) {
  // Use createApplication to bootstrap the standalone component
  const appRef = await createApplication();

  // Create the component and attach it to the DOM
  const componentRef = appRef.bootstrap(AgentStoreShowComponent, element);

  // Pass props to the component instance
  if (props) {
    if (props.content) {
      componentRef.instance.data = props.content;
    } else if (props.data) {
      componentRef.instance.data = props.data;
    }

    // Trigger change detection manually after setting props
    appRef.tick();
  }

  // Return an unmount function
  return () => {
    appRef.destroy();
  };
}
