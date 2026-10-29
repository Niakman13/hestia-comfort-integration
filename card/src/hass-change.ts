import type {PropertyValues} from 'lit';

type Watched={connection?:unknown;themes?:{darkMode?:boolean};user?:{is_admin?:boolean};language?:string};

/** Home Assistant hands a new `hass` to every card at each state change of the home. The cards are fed by their own
 *  subscription: from `hass` they only read the connection, the dark mode, whether the user is an admin, and the language. */
export function hassMatters(changed:PropertyValues,next?:object):boolean{
  if(changed.size!==1||!changed.has('hass'))return true;
  const old=changed.get('hass') as Watched|undefined,hass=next as Watched|undefined;
  return !old||!hass||old.connection!==hass.connection||old.themes?.darkMode!==hass.themes?.darkMode||old.user?.is_admin!==hass.user?.is_admin||old.language!==hass.language;
}
