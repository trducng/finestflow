from unittest import TestCase

from theflow.context.in_memory import SimpleMemoryContext


class X:
    def __init__(self):
        self.x = 10


class TestSimpleMemoryContext(TestCase):

    def test_thread_safe(self):
        """Test if the memory context is thread safe"""
        import threading

        def run(context):
            context.set("a", 1)
            context.set("b", 2)
            context.set("c", 3)

        context = SimpleMemoryContext()
        threads = []
        for _ in range(10):
            t = threading.Thread(target=run, args=(context,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(context.get("a"), 1)
        self.assertEqual(context.get("b"), 2)
        self.assertEqual(context.get("c"), 3)

        print(context)

    def test_process_safe(self):
        """Test if the memory context is accessible and safe in multi-processing"""
        import multiprocessing

        def run(context):
            context.set("a", 1)
            context.set("b", 2)
            context.set("c", 3)
            context.set("d", X())

        context = SimpleMemoryContext()
        context.make_process_safe()
        processes = []
        for _ in range(10):
            p = multiprocessing.Process(target=run, args=(context,))
            processes.append(p)
            p.start()
            
        for p in processes:
            p.join()

        self.assertEqual(context.get("a"), 1)
        self.assertEqual(context.get("b"), 2)
        self.assertEqual(context.get("c"), 3)
        self.assertEqual(context.get("d").x, 10)

    def test_get_all(self):
        """Test it's possible to get all values from the context"""
        import multiprocessing

        def run(context):
            context.set("a", 1)
            context.set("b", 2)
            context.set("c", 3)
        
        context = SimpleMemoryContext()
        context.make_process_safe()
        processes = []
        for _ in range(10):
            p = multiprocessing.Process(target=run, args=(context,))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        self.assertEqual(context.get(None), {"a": 1, "b": 2, "c": 3})
