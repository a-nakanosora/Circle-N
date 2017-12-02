class DynamicMemberSetHelperMixin:
    def __init__(self):
        self.__member_dict__ = {}
        self.__debug_updatev_count__ = {}

    def clean_allv(self):
        for name in list( self.__member_dict__ ):
            self.cleanv(name)

    def cleanv(self, name):
        if not name in self.__member_dict__:
            raise Exception('MemberSetterMixin2 Error: cleanv no member: '+name)
        del self.__dict__[name]
        del self.__member_dict__[name]
        del self.__debug_updatev_count__[name]

    def initv(self, name, value):
        if name in self.__member_dict__:
            raise Exception('MemberSetterMixin2 Error: the member is already set: '+name)
        self.__dict__[name] = value
        self.__member_dict__[name] = True
        self.__debug_updatev_count__[name] = 0

    def updatev(self, name, value, ref_check=True):
        if not name in self.__member_dict__:
            raise Exception('MemberSetterMixin2 Error: no init member: '+name)
        if ref_check:
            self.__check_id_already_exists__(name, value)

        self.__dict__[name] = value
        self.__debug_updatev_count__[name] += 1

    def __check_id_already_exists__(self, name, value):
        def is_mutable(obj):
            try: hash(obj); return not hasattr(obj, '__dict__')
            except TypeError: return False
        if not is_mutable(value):
            for n in self.__dict__:
                if id(self.__dict__[n]) == id(value) and n != name:
                    raise Exception('MemberSetterMixin2 Error: same address object refers: %s and %s' % (name, n))

    def existv(self, name):
        return name in self.__dict__

    def debug_show_updatev_counts(self):
        for n in self.__debug_updatev_count__:
            print('count of %s : %d' % (n, self.__debug_updatev_count__[n]))

class Object:pass

class ObjectV(DynamicMemberSetHelperMixin):pass