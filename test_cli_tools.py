def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        'README.txt', package='__main__',
        optionflags=doctest.ELLIPSIS #|doctest.NORMALIZE_WHITESPACE,
    )

