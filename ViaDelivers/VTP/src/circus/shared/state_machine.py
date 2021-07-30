
class Transition(object):
    def __init__(self, source, target, label, validator, validator_description, callback):
        """
        :type source: State
        :type target: State
        :type label: unicode
        :type validator: function
        :type validator_description: unicode
        :type callback: function
        """
        self.source = source
        self.target = target
        self.label = label
        self.validator = validator
        self.validator_description = validator_description
        self.callback = callback

    def validate(self, *args):
        return self.validator(*args)


    def __repr__(self):
        return '<%s "%s", %s to %s>' % (
            self.__class__.__name__,
            self.label, self.source.name, self.target.name)


class Action(object):
    def __init__(self, state, label, slug, function, validator, validator_description):
        self.state = state
        self.label = label
        self.slug = slug
        self.function = function
        self.validator = validator
        self.validator_description = validator_description

    def validate(self, *args):
        return self.validator(*args)


class State(object):
    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.transitions = []
        self.actions = []

    def add_transition(self, target, label, validator, validator_description='', callback=None):
        transition = Transition(self, target, label, validator, validator_description, callback)
        self.transitions.append(transition)

    def add_action(self, label, slug, function, validator, validator_description='', ):
        action = Action(self, label, slug, function, validator, validator_description )
        self.actions.append(action)

    def __unicode__(self):
        return unicode(self.label)


class MachineError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Machine(object):
    def __init__(self, model, states, state_field, default_initial=None):
        self.model = model
        self.states = states
        self.state_field = state_field
        self.transitions = []
        for state in states.values():
            for transition in state.transitions:
                self.transitions.append(transition)
        self._set_initial(default_initial)

    def _set_initial(self, initial):
        try:
            self._update_state_from_model()
        except AttributeError:
            raise MachineError("The model for this state machine needs a state field in the database")
        if not getattr(self.model, self.state_field):
            self.state = self._update_model(initial, False)

    def _update_state_from_model(self):
        self.state = self.states.get(getattr(self.model, self.state_field))


    def _update_model(self, state, save=True):
        setattr(self.model, self.state_field, state.name)
        if save:
            self.model.save()
        self._update_state_from_model()


    def transition(self, transition):
        self._update_state_from_model()
        assert transition.source == self.state
        assert self.states[transition.target.name] == transition.target

        if transition.validator(self.model):
            self._update_model(transition.target)
            if transition.callback:
                transition.callback(self.model)
            return self.state
        else:
            raise MachineError(u"Cannot transition to %s from %s: %s" %
                               (transition.target.name, self.state.name,
                                transition.validator_description))


    def transition_to(self, target_state_name):
        for transition in self.transitions:
            if (transition.source == self.state and
                    transition.target.name == target_state_name):
                return self.transition(transition)

        raise MachineError("No transition from %s to %s found." %
                           (self.state.name, target_state_name))


    def get_transitions(self):
        return [transition for transition in self.transitions if transition.source == self.state]

    def get_valid_transitions(self):
        return [transition for transition in self.get_transitions() if transition.validate(self.model)]

    def get_invalid_transitions(self):
        return [transition for transition in self.get_transitions() if not transition.validate(self.model)]

    def get_actions(self):
        return self.state.actions

    def get_valid_actions(self):
        return [action for action in self.get_actions() if action.validate(self.model)]

    def get_invalid_actions(self):
        return [action for action in self.get_actions() if not action.validate(self.model)]

    def is_state(self, state):
        self._update_state_from_model()
        return self.state == state
